from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.db.models.job import Job
from src.db.session import get_session
from src.auth import current_active_user
from src.db.models.user import User
from src.api.v1.schemas import JobCreate, JobRead, JobUpdate
from src.db.models.candidate import Candidate
from src.db.models.interview import Interview
from src.db.models.candidate_profile import CandidateProfile
from src.core.s3 import put_object_bytes
from datetime import datetime, timedelta
import re

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None


@router.get("/", response_model=List[JobRead])
async def list_jobs(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    result = await session.execute(select(Job).where(Job.user_id == current_user.id))
    return result.scalars().all()


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    job = Job(title=job_in.title, description=job_in.description, user_id=current_user.id)
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

        # Upload resume to S3 under separate prefix (dev fallback if S3 is not configured)
        # Use "cvs/{YYYY}/{MM}/{job_id}/..." rather than uploads/
        date_prefix = datetime.utcnow().strftime("%Y/%m")
        safe_name = (f.filename or "resume").replace("/", "-")
        key = f"cvs/{date_prefix}/{job.id}/{int(datetime.utcnow().timestamp())}_{safe_name}"
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