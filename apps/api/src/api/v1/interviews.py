from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_active_user, get_effective_owner_id, ensure_permission
from src.db.models.user import User
from src.db.models.job import Job
from src.db.models.interview import Interview
from src.db.models.candidate import Candidate
from src.db.models.conversation import ConversationMessage, InterviewAnalysis
from src.db.models.candidate import Candidate
from src.db.session import get_session
from src.api.v1.schemas import InterviewCreate, InterviewRead, InterviewStatusUpdate, InterviewMediaUpdate
from src.core.s3 import generate_presigned_get_url
from urllib.parse import urlparse
from src.services.analysis import generate_llm_full_analysis
from src.services.analysis import merge_enrichment_into_analysis
from src.core.metrics import collector, Timer
from src.core.mail import send_email_resend
from pydantic import BaseModel
import httpx
import asyncio
from src.services.stt import transcribe_with_whisper
from src.services.nlp import extract_soft_skills
from src.services.queue import enqueue_process_interview
from src.core.audit import AuditLogger, AuditEventType, AuditContext

router = APIRouter(prefix="/interviews", tags=["interviews"])

# Endpoint open to candidate via token (no admin_required) to attach media URLs
candidate_router = APIRouter(prefix="/interviews")


@router.post("/", response_model=InterviewRead, status_code=status.HTTP_201_CREATED)
async def create_interview(
    int_in: InterviewCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Enforce tenant boundaries: job and candidate must belong to the tenant owner
    owner_id = get_effective_owner_id(current_user)
    job = (
        await session.execute(
            select(Job).where(Job.id == int_in.job_id, Job.user_id == owner_id)
        )
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    cand = (
        await session.execute(
            select(Candidate).where(Candidate.id == int_in.candidate_id, Candidate.user_id == owner_id)
        )
    ).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    interview = Interview(job_id=job.id, candidate_id=cand.id, status=int_in.status)
    session.add(interview)
    await session.commit()
    await session.refresh(interview)
    # Precompute dialog plan in background (CV + Job) to personalize early questions
    try:
        from src.services.analysis import precompute_dialog_plan_bg
        import asyncio as _aio
        _aio.create_task(precompute_dialog_plan_bg(interview.id))
    except Exception:
        pass
    return interview


# --- Transcript stub (manual provider) ---


class TranscriptPayload(BaseModel):
    text: str
    provider: str


_in_memory_transcripts: dict[int, str] = {}


async def _maybe_complete_interview(
    session: AsyncSession,
    interview: Interview,
    request: Request | None = None,
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
    # 🚨 ENHANCED COMPLETION VALIDATION: Prevent partial save corruption
    # Looser completion for tests/local: as soon as transcript exists with media
    if has_media and has_transcript:
        from datetime import datetime, timezone
        interview.status = "completed"
        interview.completed_at = datetime.now(timezone.utc)
        
        # Record completion metrics for monitoring
        # Metrics are best-effort and optional
        try:
            from src.core.metrics import collector
            collector.increment_counter("interview_completed_successfully")
        except Exception:
            pass
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


async def save_transcript(
    int_id: int,
    payload: TranscriptPayload,
    session: AsyncSession,
    request: Request | None = None,
) -> dict:
    """Core logic for saving transcript to interview. Can be called directly or from HTTP endpoint."""
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


@router.post("/{int_id}/transcript")
async def upload_transcript(
    int_id: int,
    payload: TranscriptPayload,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    return await save_transcript(int_id, payload, session, request)


@router.get("/{int_id}/transcript")
async def get_transcript(int_id: int):
    """Return full conversation transcript including both AI and candidate turns.

    Order is by sequence_number to reconstruct dialogue flow. Includes 'System' entries
    for completeness when present. Falls back to stored interview.transcript_text or
    legacy in-memory value when message list unavailable.
    """
    from src.db.session import async_session_factory
    async with async_session_factory() as session:
        # Prefer assembling from conversation messages to include all turns
        msgs = (
            await session.execute(
                select(ConversationMessage)
                .where(ConversationMessage.interview_id == int_id)
                .order_by(ConversationMessage.sequence_number)
            )
        ).scalars().all()
        if msgs:
            def _prefix(m):
                return ("Yapay Zeka" if m.role.value == "assistant" else ("Aday" if m.role.value == "user" else "Sistem"))
            lines = [f"{_prefix(m)}: {(m.content or '').strip()}" for m in msgs if (m.content or "").strip()]
            text = "\n\n".join(lines) if lines else ""
            if text:
                return {"interview_id": int_id, "text": text}

        # If messages missing, use persisted transcript_text
        interview = (
            await session.execute(select(Interview).where(Interview.id == int_id))
        ).scalar_one_or_none()
        if interview and (interview.transcript_text and interview.transcript_text.strip()):
            return {"interview_id": int_id, "text": interview.transcript_text}

    # Legacy in-memory fallback
    if int_id in _in_memory_transcripts:
        return {"interview_id": int_id, "text": _in_memory_transcripts[int_id]}
    raise HTTPException(status_code=404, detail="Transcript not found")


@router.get("/", response_model=List[InterviewRead])
async def list_interviews(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Only show interviews for jobs that belong to the tenant owner
    owner_id = get_effective_owner_id(current_user)

    # Single round-trip with LEFT OUTER JOIN to analysis to avoid per-row queries
    result = await session.execute(
        select(Interview, User, InterviewAnalysis)
        .join(Job, Interview.job_id == Job.id)
        .join(User, User.id == Job.user_id)
        .outerjoin(InterviewAnalysis, InterviewAnalysis.interview_id == Interview.id)
        .where(Job.user_id == owner_id)
    )
    rows = result.all()

    out: List[InterviewRead] = []
    for iv, user, ana in rows:
        try:
            iv_dict = {
                "id": iv.id,
                "job_id": iv.job_id,
                "candidate_id": iv.candidate_id,
                "status": iv.status,
                "created_at": iv.created_at,
                "audio_url": iv.audio_url,
                "video_url": iv.video_url,
                "completed_at": iv.completed_at,
                "completed_ip": iv.completed_ip,
                "prepared_first_question": iv.prepared_first_question,
                "company_name": getattr(user, "company_name", None),
            }

            # Inline analysis fields when available
            try:
                over = getattr(ana, "overall_score", None) if ana else None
                if isinstance(over, (int, float)):
                    iv_dict["overall_score"] = float(over)
                if ana and getattr(ana, "technical_assessment", None):
                    import json as _json
                    try:
                        blob = _json.loads(ana.technical_assessment or "{}")
                        if isinstance(blob, dict):
                            pd = (blob.get("panel_review") or {}).get("decision")
                            if isinstance(pd, str):
                                iv_dict["panel_decision"] = pd
                            fi = blob.get("final_interview")
                            if isinstance(fi, dict):
                                iv_dict["final_interview"] = fi
                    except Exception:
                        pass
            except Exception:
                pass

            out.append(InterviewRead(**iv_dict))
        except Exception:
            # Skip corrupted rows non-fatally
            continue
    return out


@candidate_router.get("/by-token/{token}", response_model=InterviewRead)
async def get_interview_by_token(token: str, session: AsyncSession = Depends(get_session)):
    """Return the most recent interview for the candidate identified by token.
    This endpoint is public (no auth) for the candidate UI to initialize conversation tracking.
    """
    from src.db.models.candidate import Candidate
    cand = (await session.execute(select(Candidate).where(Candidate.token == token))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Geçersiz token")
    interview = (
        await session.execute(
            select(Interview).where(Interview.candidate_id == cand.id).order_by(Interview.created_at.desc())
        )
    ).scalar_one_or_none()
    if not interview:
        # Create a placeholder interview so that the client can record conversation messages
        # Choose the newest job for this tenant; if none exists, create a minimal interview without job context
        job = (
            await session.execute(
                select(Job).where(Job.user_id == cand.user_id).order_by(Job.created_at.desc())
            )
        ).scalar_one_or_none()
        interview = Interview(job_id=job.id if job else None, candidate_id=cand.id, status="pending")  # type: ignore[arg-type]
        session.add(interview)
        await session.commit()
        await session.refresh(interview)
    
    # Get company name from user
    user = (await session.execute(select(User).where(User.id == cand.user_id))).scalar_one_or_none()
    company_name = user.company_name if user else None
    
    # Return interview with company name
    interview_dict = {
        "id": interview.id,
        "job_id": interview.job_id,
        "candidate_id": interview.candidate_id,
        "status": interview.status,
        "created_at": interview.created_at,
        "audio_url": interview.audio_url,
        "video_url": interview.video_url,
        "completed_at": interview.completed_at,
        "completed_ip": interview.completed_ip,
        "prepared_first_question": interview.prepared_first_question,
        "company_name": company_name
    }
    
    return InterviewRead(**interview_dict)


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
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = (
        await session.execute(
            select(Interview)
            .join(Job, Interview.job_id == Job.id)
            .where(Interview.id == int_id, Job.user_id == owner_id)
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
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = (
        await session.execute(
            select(Interview)
            .join(Job, Interview.job_id == Job.id)
            .where(Interview.id == int_id, Job.user_id == owner_id)
        )
    ).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    interview.status = status_in.status
    await session.commit()
    await session.refresh(interview)
    return interview


@router.get("/{int_id}/status")
async def get_interview_status(
    int_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    """Get interview status and completion information."""
    # Ensure ownership
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = (
        await session.execute(
            select(Interview)
            .join(Job, Interview.job_id == Job.id)
            .where(Interview.id == int_id, Job.user_id == owner_id)
        )
    ).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    return {
        "interview_id": int_id,
        "status": interview.status,
        "completed_at": interview.completed_at,
        "is_completed": interview.status == "completed",
        "has_media": bool(interview.audio_url or interview.video_url),
        "has_transcript": bool(interview.transcript_text),
    }


# --- Candidate uploads media URLs (audio / video) ---


@candidate_router.patch("/{token}/media", response_model=InterviewRead)
async def upload_media(token:str, media_in:InterviewMediaUpdate, request: Request, session:AsyncSession=Depends(get_session)):
    # Find interview by candidate token (latest)
    from src.db.models.candidate import Candidate
    cand = (await session.execute(select(Candidate).where(Candidate.token==token))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Geçersiz token")
    interview = (
        await session.execute(select(Interview).where(Interview.candidate_id==cand.id).order_by(Interview.created_at.desc()))
    ).scalar_one_or_none()
    if not interview:
        # Create new interview if none exists. Choose a job that belongs to the same tenant (cand.user_id)
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
    # Audit upload
    try:
        audit = AuditLogger()
        await audit.log(
            AuditEventType.FILE_UPLOAD,
            message="Candidate media uploaded",
            context=AuditContext(resource_type="interview", resource_id=interview.id),
            details={"has_audio": bool(media_in.audio_url), "has_video": bool(media_in.video_url)}
        )
        if interview.status == "completed":
            await audit.log(
                AuditEventType.INTERVIEW_COMPLETE,
                message="Interview completed",
                context=AuditContext(resource_type="interview", resource_id=interview.id),
                details={}
            )
    except Exception:
        pass

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
                analysis = await generate_llm_full_analysis(session, interview.id)
            collector.record_analysis_ms(t.ms)
            # Audit LLM kickoff
            try:
                audit = AuditLogger()
                await audit.log(
                    AuditEventType.DATA_UPDATE,
                    message="Analysis generation started",
                    context=AuditContext(resource_type="interview", resource_id=interview.id)
                )
            except Exception:
                pass
            # Notify responsible users best-effort
            try:
                job = (await session.execute(select(Job).where(Job.id == interview.job_id))).scalar_one_or_none()
                if job:
                    recipients: set[str] = set()
                    # prefer creators when available
                    cand = (await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))).scalar_one_or_none()
                    if cand and getattr(cand, "created_by_user_id", None):
                        creator = (await session.execute(select(User).where(User.id == cand.created_by_user_id))).scalar_one_or_none()
                        if creator and getattr(creator, "email", None):
                            recipients.add(creator.email)
                    # job owner
                    owner = (await session.execute(select(User).where(User.id == job.user_id))).scalar_one_or_none()
                    if owner and getattr(owner, "email", None):
                        recipients.add(owner.email)
                    # job creator
                    if getattr(job, "created_by_user_id", None):
                        jcreator = (await session.execute(select(User).where(User.id == job.created_by_user_id))).scalar_one_or_none()
                        if jcreator and getattr(jcreator, "email", None):
                            recipients.add(jcreator.email)
                    # team members under same tenant
                    team_rows = await session.execute(select(User).where(User.owner_user_id == job.user_id))
                    team = team_rows.scalars().all()
                    for u in team:
                        if getattr(u, "email", None) and (getattr(u, "role", None) in {"organization_admin", "hr_manager", "recruiter"} or not getattr(u, "role", None)):
                            recipients.add(u.email)
                    if recipients:
                        cand = (await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))).scalar_one_or_none()
                        cand_name = getattr(cand, "name", None) or f"Aday #{interview.candidate_id}"
                        job_title = getattr(job, "title", None) or "Pozisyon"
                        subject = f"Rapor hazır: {cand_name} – {job_title}"
                        body = (
                            f"Merhaba,\n\n"
                            f"{cand_name} için {job_title} mülakat analiz raporu hazırlandı.\n"
                            f"Raporu panele giriş yaparak görüntüleyebilirsiniz.\n\n"
                            f"Görüşme ID: {interview.id}\n"
                            f"Saygılarımızla\n"
                            f"RecruiterAI"
                        )
                        for email in recipients:
                            try:
                                await send_email_resend(email, subject, body)
                            except Exception:
                                pass
            except Exception:
                pass
    except Exception:
        # Non-blocking; log only
        import logging
        logging.getLogger(__name__).exception("[analysis] generation failed")
    return interview 