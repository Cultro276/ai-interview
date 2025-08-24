from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_active_user
from src.db.models.user import User
from src.db.models.job import Job
from src.db.models.interview import Interview
from src.db.models.candidate import Candidate
from src.db.models.conversation import ConversationMessage
from src.db.models.candidate import Candidate
from src.db.session import get_session
from src.api.v1.schemas import InterviewCreate, InterviewRead, InterviewStatusUpdate, InterviewMediaUpdate
from src.core.s3 import generate_presigned_get_url
from urllib.parse import urlparse
from src.services.analysis import generate_rule_based_analysis
from src.services.analysis import merge_enrichment_into_analysis
from src.core.metrics import collector, Timer
from pydantic import BaseModel
import httpx
import asyncio
from src.services.stt import transcribe_with_whisper
from src.services.nlp import extract_soft_skills
from src.services.queue import enqueue_process_interview

router = APIRouter(prefix="/interviews", tags=["interviews"])

# Endpoint open to candidate via token (no admin_required) to attach media URLs
candidate_router = APIRouter(prefix="/interviews")


@router.post("/", response_model=InterviewRead, status_code=status.HTTP_201_CREATED)
async def create_interview(
    int_in: InterviewCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Enforce tenant boundaries: job and candidate must belong to the current user
    job = (
        await session.execute(
            select(Job).where(Job.id == int_in.job_id, Job.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    cand = (
        await session.execute(
            select(Candidate).where(Candidate.id == int_in.candidate_id, Candidate.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    interview = Interview(job_id=job.id, candidate_id=cand.id, status=int_in.status)
    session.add(interview)
    await session.commit()
    await session.refresh(interview)
    return interview


# --- Transcript stub (manual provider) ---


class TranscriptPayload(BaseModel):
    text: str
    provider: str


_in_memory_transcripts: dict[int, str] = {}


async def _maybe_complete_interview(
    session: AsyncSession,
    interview: Interview,
    request: Request = None,
):
    """Mark interview as completed once media (audio or video) and transcript exist.

    Also sets candidate.used_at at completion time, and completion IP.
    """
    # Already completed → no-op
    if interview.status == "completed":
        return
    has_media = bool(interview.audio_url or interview.video_url)
    transcript_text = _in_memory_transcripts.get(interview.id) or ""
    has_transcript = bool(transcript_text.strip())
    if not has_transcript:
        # Consider DB conversation messages as transcript presence
        cm = (
            await session.execute(
                select(ConversationMessage).where(ConversationMessage.interview_id == interview.id)
            )
        ).first()
        has_transcript = cm is not None
    if has_media and has_transcript:
        from datetime import datetime, timezone
        interview.status = "completed"
        interview.completed_at = datetime.now(timezone.utc)
        try:
            ip = request.client.host if request and request.client else None
            interview.completed_ip = ip
        except Exception:
            pass
        # Mark candidate token as used at completion
        cand = (
            await session.execute(
                select(Candidate).where(Candidate.id == interview.candidate_id)
            )
        ).scalar_one_or_none()
        if cand and not cand.used_at:
            cand.used_at = interview.completed_at
        await session.commit()
        await session.refresh(interview)


@router.post("/{int_id}/transcript")
async def upload_transcript(
    int_id: int,
    payload: TranscriptPayload,
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    interview = (
        await session.execute(select(Interview).where(Interview.id == int_id))
    ).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    # Persist transcript on interview
    interview.transcript_text = payload.text or ""
    interview.transcript_provider = payload.provider or "manual"
    await session.commit()
    await session.refresh(interview)
    # Backward-compat for any in-memory consumers
    _in_memory_transcripts[int_id] = interview.transcript_text or ""
    await _maybe_complete_interview(session, interview, request)
    return {"interview_id": int_id, "length": len(interview.transcript_text or "")}


@router.get("/{int_id}/transcript")
async def get_transcript(int_id: int):
    # Prefer DB value; fallback to in-memory; if still missing, assemble from full conversation messages (assistant+user)
    from src.db.session import async_session_factory
    async with async_session_factory() as session:
        interview = (
            await session.execute(select(Interview).where(Interview.id == int_id))
        ).scalar_one_or_none()
        if interview and (interview.transcript_text and interview.transcript_text.strip()):
            return {"interview_id": int_id, "text": interview.transcript_text}

        # Assemble a full transcript from conversation messages (assistant + user)
        msgs = (
            await session.execute(
                select(ConversationMessage)
                .where(ConversationMessage.interview_id == int_id)
                .order_by(ConversationMessage.sequence_number)
            )
        ).scalars().all()
        if msgs:
            def _prefix(m):
                return ("Interviewer" if m.role.value == "assistant" else ("Candidate" if m.role.value == "user" else "System"))
            lines = [f"{_prefix(m)}: {m.content.strip()}" for m in msgs if (m.content or "").strip()]
            if lines:
                text = "\n\n".join(lines)
                return {"interview_id": int_id, "text": text}

    if int_id in _in_memory_transcripts:
        return {"interview_id": int_id, "text": _in_memory_transcripts[int_id]}
    raise HTTPException(status_code=404, detail="Transcript not found")


@router.get("/", response_model=List[InterviewRead])
async def list_interviews(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Only show interviews for jobs that belong to the current user
    result = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Job.user_id == current_user.id)
    )
    return result.scalars().all()


@candidate_router.get("/by-token/{token}", response_model=InterviewRead)
async def get_interview_by_token(token: str, session: AsyncSession = Depends(get_session)):
    """Return the most recent interview for the candidate identified by token.
    This endpoint is public (no auth) for the candidate UI to initialize conversation tracking.
    """
    from src.db.models.candidate import Candidate
    cand = (await session.execute(select(Candidate).where(Candidate.token == token))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Invalid token")
    interview = (
        await session.execute(
            select(Interview).where(Interview.candidate_id == cand.id).order_by(Interview.created_at.desc())
        )
    ).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


class MediaDownloadResponse(BaseModel):
    audio_url: str | None = None
    video_url: str | None = None


@router.get("/{int_id}/media-download-urls", response_model=MediaDownloadResponse)
async def media_download_urls(
    int_id: int,
    expires_in: int = 600,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Ensure ownership
    interview = (
        await session.execute(
            select(Interview)
            .join(Job, Interview.job_id == Job.id)
            .where(Interview.id == int_id, Job.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    def to_key(url: str | None) -> str | None:
        if not url:
            return None
        if url.startswith("s3://"):
            return url.split("/", 3)[-1]
        try:
            return urlparse(url).path.lstrip("/")
        except Exception:
            return None

    audio_key = to_key(getattr(interview, "audio_url", None))
    video_key = to_key(getattr(interview, "video_url", None))

    audio = generate_presigned_get_url(audio_key, expires=expires_in) if audio_key else None
    video = generate_presigned_get_url(video_key, expires=expires_in) if video_key else None

    return MediaDownloadResponse(audio_url=audio, video_url=video)


@router.patch("/{int_id}/status", response_model=InterviewRead)
async def update_status(
    int_id: int,
    status_in: InterviewStatusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Ensure the interview belongs to a job owned by the current user
    interview = (
        await session.execute(
            select(Interview)
            .join(Job, Interview.job_id == Job.id)
            .where(Interview.id == int_id, Job.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    interview.status = status_in.status
    await session.commit()
    await session.refresh(interview)
    return interview


# --- Candidate uploads media URLs (audio / video) ---


@candidate_router.patch("/{token}/media", response_model=InterviewRead)
async def upload_media(token:str, media_in:InterviewMediaUpdate, session:AsyncSession=Depends(get_session), request: Request = None):
    # Find interview by candidate token (latest)
    from src.db.models.candidate import Candidate
    cand = (await session.execute(select(Candidate).where(Candidate.token==token))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Invalid token")
    interview = (
        await session.execute(select(Interview).where(Interview.candidate_id==cand.id).order_by(Interview.created_at.desc()))
    ).scalar_one_or_none()
    if not interview:
        # Create new interview if none exists. Choose a job that belongs to the same tenant (cand.user_id)
        from src.db.models.job import Job
        job = (
            await session.execute(
                select(Job).where(Job.user_id == cand.user_id).order_by(Job.created_at.desc())
            )
        ).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=400, detail="No job available to attach interview")
        interview = Interview(job_id=job.id, candidate_id=cand.id, status="pending")
        session.add(interview)
        await session.flush()
    if media_in.audio_url:
        interview.audio_url = media_in.audio_url
    if media_in.video_url:
        interview.video_url = media_in.video_url
    await session.commit()
    await session.refresh(interview)
    # Complete only when transcript also exists
    await _maybe_complete_interview(session, interview, request)

    # Background STT: if transcript missing and audio exists, fetch and transcribe
    try:
        has_transcript = bool(getattr(interview, "transcript_text", None)) or bool(_in_memory_transcripts.get(interview.id))
        if (not has_transcript) and interview.audio_url:
            def _to_key(url: str | None) -> str | None:
                if not url:
                    return None
                if url.startswith("s3://"):
                    return url.split("/", 3)[-1]
                try:
                    from urllib.parse import urlparse as _urlparse
                    return _urlparse(url).path.lstrip("/")
                except Exception:
                    return None

            key = _to_key(interview.audio_url)
            if key:
                # Prefer queue-based processing for durability
                enqueue_process_interview(interview.id)
    except Exception:
        pass

    # Metrics: estimate upload latency from presign to completion using candidate token
    try:
        collector.record_upload_completion(token)
    except Exception:
        pass

    # Auto-generate analysis after media is saved (if completed)
    try:
        if interview.status == "completed":
            with Timer() as t:
                await generate_rule_based_analysis(session, interview.id)
            collector.record_analysis_ms(t.ms)
    except Exception:
        # Non-blocking; log only
        import logging
        logging.getLogger(__name__).exception("[analysis] generation failed")
    return interview 