# pyright: reportMissingImports=false, reportMissingModuleSource=false
from typing import List
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.job import Job
from src.db.session import get_session
from src.auth import current_active_user
from src.db.models.user import User
from src.api.v1.schemas import JobCreate, JobRead, JobUpdate, CandidateCreate, CandidateRead
from src.db.models.candidate import Candidate
from src.db.models.interview import Interview
from src.db.models.candidate_profile import CandidateProfile
from src.db.models.conversation import InterviewAnalysis
from src.core.s3 import put_object_bytes, generate_presigned_put_url_at_key
from src.core.gemini import extract_requirements_from_text
from datetime import datetime, timedelta
import re

# Hint pyright that 3rd-party imports are available at runtime
if TYPE_CHECKING:
    import fastapi  # noqa: F401
    import sqlalchemy  # noqa: F401
    import pydantic  # noqa: F401

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=List[JobRead])
async def list_jobs(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    result = await session.execute(select(Job).where(Job.user_id == current_user.id))
    return result.scalars().all()


@router.get("/{job_id}/requirements-config")
async def get_requirements_config(job_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(current_active_user)):
    job = (await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        return job.requirements_config  # type: ignore[attr-defined]
    except Exception:
        return None


@router.put("/{job_id}/requirements-config")
async def set_requirements_config(job_id: int, payload: dict, session: AsyncSession = Depends(get_session), current_user: User = Depends(current_active_user)):
    job = (await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    setattr(job, "requirements_config", payload)
    await session.commit()
    return {"ok": True}


@router.get("/{job_id}/rubric-weights")
async def get_rubric_weights(job_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(current_active_user)):
    job = (await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        return job.rubric_weights  # type: ignore[attr-defined]
    except Exception:
        return None


@router.put("/{job_id}/rubric-weights")
async def set_rubric_weights(job_id: int, payload: dict, session: AsyncSession = Depends(get_session), current_user: User = Depends(current_active_user)):
    job = (await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    setattr(job, "rubric_weights", payload)
    await session.commit()
    return {"ok": True}


class ExtractReqBody(BaseModel):
    job_text: str


@router.post("/{job_id}/extract-requirements")
async def extract_requirements(job_id: int, payload: ExtractReqBody, session: AsyncSession = Depends(get_session), current_user: User = Depends(current_active_user)):
    job = (await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    data = await extract_requirements_from_text(payload.job_text)
    # apply but do not overwrite if fields are missing
    if data.get("requirements_config"):
        job.requirements_config = data["requirements_config"]
    if data.get("rubric_weights"):
        job.rubric_weights = data["rubric_weights"]
    await session.commit()
    await session.refresh(job)
    return {"requirements_config": job.requirements_config, "rubric_weights": job.rubric_weights}


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    expiry = job_in.expires_in_days if (job_in.expires_in_days and job_in.expires_in_days > 0) else 7
    job = Job(
        title=job_in.title,
        description=job_in.description,
        user_id=current_user.id,
        default_invite_expiry_days=expiry,
        requirements_config=job_in.requirements_config,
        rubric_weights=job_in.rubric_weights,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


@router.put("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: int, 
    job_in: JobUpdate, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    result = await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for field, value in job_in.dict(exclude_unset=True).items():
        if field == "expires_in_days" and value is not None:
            job.default_invite_expiry_days = value
        elif field in {"title", "description", "requirements_config", "rubric_weights"}:
            setattr(job, field, value)
    await session.commit()
    await session.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    result = await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await session.delete(job)
    await session.commit()


# --- Bulk CV upload --

class BulkUploadResponse(BaseModel):
    created: int
    candidates: List[int]


def _extract_email(text: str) -> str | None:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return m.group(0) if m else None


@router.post("/{job_id}/candidates/bulk-upload", response_model=BulkUploadResponse)
async def bulk_upload_candidates(
    job_id: int,
    files: List[UploadFile] = File(...),
    expires_in_days: int = 7,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    job = (await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    created_ids: List[int] = []

    for f in files:
        content = await f.read()
        text = ""
        try:
            if f.content_type and f.content_type.startswith("text"):
                text = content.decode(errors="ignore")
        except Exception:
            text = ""

        # Heuristics for name/email
        email = _extract_email(text) or _extract_email(f.filename or "")
        base = (f.filename or "candidate").rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
        name = base.title()[:255]

        # Upload resume under cvs/{job_id}/... fixed path
        safe_name = (f.filename or "resume").split("/")[-1]
        key = f"cvs/{job.id}/{int(datetime.utcnow().timestamp())}_{safe_name}"
        try:
            resume_url = put_object_bytes(key, content, f.content_type or "application/octet-stream")
        except Exception:
            # Smooth-dev: allow missing S3 by skipping resume storage
            resume_url = None

        # Create candidate
        cand = Candidate(
            user_id=current_user.id,
            name=name or "Candidate",
            email=email or f"no-email-{int(datetime.utcnow().timestamp())}@example.com",
            resume_url=resume_url,
            status="pending",
            token="",
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
        )
        session.add(cand)
        await session.flush()

        # Ensure token after id exists
        from uuid import uuid4
        cand.token = uuid4().hex

        # Link to job via Interview
        interview = Interview(job_id=job.id, candidate_id=cand.id, status="pending")
        session.add(interview)

        # Save profile metadata only (no raw file in DB when using S3)
        profile = CandidateProfile(
            candidate_id=cand.id,
            resume_text=text or None,
            resume_file=None,
            file_name=f.filename,
            content_type=f.content_type,
            file_size=len(content),
        )
        session.add(profile)

        await session.commit()
        created_ids.append(cand.id)

    return BulkUploadResponse(created=len(created_ids), candidates=created_ids) 


# --- Single candidate creation bound to a job ---


@router.post("/{job_id}/candidates", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate_for_job(
    job_id: int,
    cand_in: CandidateCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Ensure job belongs to current user
    job = (
        await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Create candidate (mimic candidates.create flow)
    from uuid import uuid4
    from src.core.mail import send_email_resend
    expires_days = cand_in.expires_in_days or job.default_invite_expiry_days or 7
    candidate = Candidate(
        user_id=current_user.id,
        name=cand_in.name,
        email=cand_in.email,
        resume_url=cand_in.resume_url,
        status="pending",
        token=uuid4().hex,
        expires_at=datetime.utcnow() + timedelta(days=expires_days),
    )
    session.add(candidate)
    await session.flush()

    # Link to job via Interview
    interview = Interview(job_id=job.id, candidate_id=candidate.id, status="pending")
    session.add(interview)
    await session.commit()
    await session.refresh(candidate)

    # Best-effort invite email
    try:
        await send_email_resend(
            candidate.email,
            "Interview Invitation",
            (
                f"Merhaba {candidate.name},\n\n"
                f"Mülakatınızı başlatmak için bağlantı:\nhttp://localhost:3000/interview/{candidate.token}\n\n"
                f"Bağlantı {expires_days} gün geçerlidir."
            ),
        )
    except Exception:
        pass
    print(f"[INVITE LINK] http://localhost:3000/interview/{candidate.token}")
    return candidate


# --- Single candidate with CV presign ---


class SingleCandidatePresignRequest(BaseModel):
    file_name: str
    content_type: str


@router.post("/{job_id}/candidates/presign-cv")
async def presign_single_candidate_cv(
    job_id: int,
    payload: SingleCandidatePresignRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Verify job ownership
    job = (
        await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    safe_name = (payload.file_name or "resume").split("/")[-1]
    key = f"cvs/{job.id}/{int(datetime.utcnow().timestamp())}_{safe_name}"
    try:
        presigned = generate_presigned_put_url_at_key(key, payload.content_type)
        return {"url": presigned["url"], "key": presigned["key"]}
    except Exception:
        # Dev fallback – when S3 not configured
        url = f"http://localhost:8000/dev-upload/{key}"
        return {"url": url, "key": key}


# --- Leaderboard for a job ---


class LeaderboardItem(BaseModel):
    candidate_id: int
    candidate_name: str | None
    interview_id: int
    overall_score: float | None = None
    communication_score: float | None = None
    technical_score: float | None = None
    cultural_fit_score: float | None = None


@router.get("/{job_id}/leaderboard", response_model=List[LeaderboardItem])
async def job_leaderboard(
    job_id: int,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Verify ownership
    job = (
        await session.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await session.execute(
        select(
            Interview.id.label("interview_id"),
            Candidate.id.label("candidate_id"),
            Candidate.name.label("candidate_name"),
            InterviewAnalysis.overall_score,
            InterviewAnalysis.communication_score,
            InterviewAnalysis.technical_score,
            InterviewAnalysis.cultural_fit_score,
        )
        .join(Candidate, Interview.candidate_id == Candidate.id)
        .outerjoin(InterviewAnalysis, InterviewAnalysis.interview_id == Interview.id)
        .where(Interview.job_id == job.id)
        .order_by(InterviewAnalysis.overall_score.desc().nullslast(), Interview.id.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        LeaderboardItem(
            interview_id=r.interview_id,
            candidate_id=r.candidate_id,
            candidate_name=r.candidate_name,
            overall_score=r.overall_score,
            communication_score=r.communication_score,
            technical_score=r.technical_score,
            cultural_fit_score=r.cultural_fit_score,
        )
        for r in rows
    ]