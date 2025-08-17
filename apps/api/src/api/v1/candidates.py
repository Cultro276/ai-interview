from typing import List
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

from src.auth import current_active_user
from src.db.models.user import User
from src.api.v1.schemas import CandidateCreate, CandidateRead, CandidateUpdate
from src.core.s3 import generate_presigned_get_url
from src.core.mail import send_email_resend
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
    rows: List[Candidate] = list(result.scalars().all())
    # Sanitize potentially invalid emails to avoid 500 due to response model validation
    safe_list: List[CandidateRead] = []
    for cand in rows:
        email_value = cand.email or ""
        if "@" not in email_value:
            email_value = f"invalid+{cand.id}@example.com"
        try:
            safe_list.append(CandidateRead.model_validate({
                "id": cand.id,
                "user_id": cand.user_id,
                "name": cand.name,
                "email": email_value,
                "resume_url": cand.resume_url,
                "created_at": cand.created_at,
            }))
        except Exception:
            # As last resort, skip the bad record
            continue
    return safe_list


@router.post("/", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate_in: CandidateCreate, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    candidate_data = candidate_in.dict(exclude={'expires_in_days'})
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
    try:
        await send_email_resend(
            candidate.email,
            "Interview Invitation",
            (
                f"Merhaba {candidate.name},\n\n"
                f"Mülakatınızı başlatmak için bağlantı:\nhttp://localhost:3000/interview/{candidate.token}\n\n"
                f"Bağlantı {candidate_in.expires_in_days} gün geçerlidir."
            ),
        )
    except Exception:
        pass
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
    subj = (payload.subject if payload else None) or "Interview Invitation"
    link = f"http://localhost:3000/interview/{cand.token}"
    body = (payload.body_text if payload else None) or (
        f"Merhaba {cand.name},\n\n"
        f"Mülakatınızı başlatmak için aşağıdaki bağlantıyı kullanın:\n{link}\n\n"
        f"Bağlantı {effective_expiry or 7} gün geçerlidir."
    )
    await send_email_resend(cand.email, subj, body)
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