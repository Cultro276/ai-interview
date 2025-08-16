from typing import List
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr

from src.auth import current_active_user
from src.db.models.user import User
from src.api.v1.schemas import CandidateCreate, CandidateRead, CandidateUpdate
from src.core.s3 import generate_presigned_get_url
from urllib.parse import urlparse
from src.db.models.candidate import Candidate
from src.db.session import get_session

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/", response_model=List[CandidateRead])
async def list_candidates(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    result = await session.execute(select(Candidate).where(Candidate.user_id == current_user.id))
    return result.scalars().all()


@router.post("/", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate_in: CandidateCreate, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    candidate_data = candidate_in.dict(exclude={'expires_in_days'})
    # Email required but not strictly validated; accept as-is
    candidate = Candidate(**candidate_data, user_id=current_user.id)
    candidate.token = uuid4().hex
    candidate.expires_at = datetime.utcnow() + timedelta(days=candidate_in.expires_in_days)
    session.add(candidate)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    await session.refresh(candidate)
    # Otomatik e-posta gönderimi (mock): gerçek hayatta SES/Sendgrid entegrasyonu kullanılacak
    print("[MAIL MOCK] To:", candidate.email)
    print("Subject:", "Interview Invitation")
    print("Body:", f"Please join your interview using this link (valid {candidate_in.expires_in_days} days): http://localhost:3000/interview/{candidate.token}")
    return candidate


class SendLinkRequest(BaseModel):
    subject: str | None = None
    body_text: str | None = None
    expires_in_days: int | None = None


# resend link
@router.post("/{cand_id}/send-link", dependencies=[Depends(current_active_user)])
async def resend_link(
    cand_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
    expires_in_days: int | None = None,
    payload: SendLinkRequest | None = None,
):
    cand = (await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == current_user.id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    # Optionally update expiry
    effective_expiry = expires_in_days
    if payload and payload.expires_in_days is not None:
        effective_expiry = payload.expires_in_days
    if effective_expiry and effective_expiry > 0:
        cand.expires_at = datetime.utcnow() + timedelta(days=effective_expiry)
        await session.commit()
    subj = payload.subject if payload else None
    body = payload.body_text if payload else None
    print("[MAIL MOCK] To:", cand.email)
    print("Subject:", subj or "Interview Invitation")
    print("Body:", body or f"Please join your interview using this link: http://localhost:3000/interview/{cand.token}")
    print(f"Link: http://localhost:3000/interview/{cand.token}")
    return {"detail":"sent"}


@router.get("/{cand_id}/resume-download-url")
async def resume_download_url(
    cand_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
    expires_in: int = 300,
):
    cand = (await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == current_user.id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not cand.resume_url:
        raise HTTPException(status_code=404, detail="No resume available for this candidate")
    # Support both s3:// and https presigned URLs stored directly
    if cand.resume_url.startswith("s3://"):
        parsed = urlparse(cand.resume_url)
        key = parsed.path.lstrip("/")
        url = generate_presigned_get_url(key, expires=expires_in)
        return {"url": url}
    # Already a public/proxied URL
    return {"url": cand.resume_url}


@router.put("/{cand_id}", response_model=CandidateRead)
async def update_candidate(
    cand_id: int, 
    cand_in: CandidateUpdate, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    cand = (await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == current_user.id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for field, value in cand_in.dict(exclude_unset=True).items():
        setattr(cand, field, value)
    await session.commit()
    await session.refresh(cand)
    return cand


@router.delete("/{cand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    cand_id: int, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    cand = (await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == current_user.id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    await session.delete(cand)
    await session.commit() 