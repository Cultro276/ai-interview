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
from src.db.models.candidate_profile import CandidateProfile
from src.db.models.conversation import ConversationMessage
from src.db.models.interview import Interview
from src.services.nlp import parse_resume_bytes
from sqlalchemy import select as _select
import httpx
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
    # If caller didn't specify, fallback to 7 days
    candidate.expires_at = datetime.utcnow() + timedelta(days=candidate_in.expires_in_days or 7)
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
    # Always log the invite link for local testing
    import logging
    logging.getLogger(__name__).info("[INVITE LINK] /interview/%s", candidate.token)
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
    # Always log the invite link for local testing
    import logging
    logging.getLogger(__name__).info("[INVITE LINK] %s", link)
    return {"detail":"sent"}


class FinalInviteRequest(BaseModel):
    subject: str | None = None
    body_text: str | None = None


@router.post("/{cand_id}/notify-final")
async def notify_final(
    cand_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
    payload: FinalInviteRequest | None = None,
):
    cand = (
        await session.execute(
            select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    subj = (payload.subject if payload else None) or "Final Interview Invitation"
    body = (payload.body_text if payload else None) or (
        f"Merhaba {cand.name},\n\nFinal görüşmeye davet etmek isteriz. Uygun olduğunuz zamanları paylaşabilir misiniz?\n\nSaygılarımızla"
    )
    await send_email_resend(cand.email, subj, body)
    return {"detail": "final_invite_sent"}


@router.get("/{cand_id}/invite-link")
async def get_invite_link(
    cand_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    cand = (await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == current_user.id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    url = f"http://localhost:3000/interview/{cand.token}"
    return {"url": url, "token": cand.token, "expires_at": cand.expires_at}


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
    # Support raw S3 key, s3://bucket/key, and s3://key (legacy)
    ru = cand.resume_url
    if ru.startswith("s3://"):
        parsed = urlparse(ru)
        netloc = (parsed.netloc or "").strip()
        path = parsed.path.lstrip("/")
        if netloc and path:
            # s3://bucket/key → use path
            key = path
        elif netloc and not path:
            # unlikely: s3://key-without-slash
            key = netloc
        else:
            # s3://prefix/path form stored as s3://{prefix}/{rest}
            # Recover full key as netloc + path
            key = f"{netloc}/{path}".strip("/")
        url = generate_presigned_get_url(key, expires=expires_in)
        return {"url": url}
    # If value looks like an S3 key (contains '/'), presign directly
    if "/" in ru and not ru.startswith("http"):
        url = generate_presigned_get_url(ru.lstrip("/"), expires=expires_in)
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


# --- Parse/Backfill resume text for existing candidate ---


@router.post("/{cand_id}/parse-resume", response_model=CandidateRead)
async def parse_resume_now(
    cand_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    cand = (
        await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == current_user.id))
    ).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Ensure a profile row exists
    prof = (
        await session.execute(_select(CandidateProfile).where(CandidateProfile.candidate_id == cand.id))
    ).scalar_one_or_none()
    if not prof:
        prof = CandidateProfile(candidate_id=cand.id)
        session.add(prof)
        await session.flush()

    parsed_text: str | None = None

    # 1) If resume_url exists, fetch via presigned GET and parse
    try:
        if cand.resume_url and cand.resume_url.strip():
            def _to_key(url: str) -> str | None:
                if url.startswith("s3://"):
                    from urllib.parse import urlparse as _up
                    p = _up(url)
                    return p.path.lstrip("/")
                try:
                    from urllib.parse import urlparse as _up
                    p = _up(url)
                    return p.path.lstrip("/")
                except Exception:
                    return None
            key = _to_key(cand.resume_url)
            if key:
                presigned = generate_presigned_get_url(key, expires=180)
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(presigned)
                    resp.raise_for_status()
                    parsed_text = parse_resume_bytes(resp.content, resp.headers.get("Content-Type"), cand.resume_url)
    except Exception:
        parsed_text = None

    # 2) Else, if raw file is stored in DB (legacy path), parse from there
    if not parsed_text and getattr(prof, "resume_file", None):
        try:
            parsed_text = parse_resume_bytes(prof.resume_file or b"", prof.content_type, prof.file_name)
        except Exception:
            parsed_text = None

    # 3) Fallback: synthesize minimal profile from existing conversation answers
    if not parsed_text:
        try:
            msgs = (
                await session.execute(
                    _select(ConversationMessage)
                    .where(ConversationMessage.interview_id.in_(
                        _select(Interview.id).where(Interview.candidate_id == cand.id)
                    ))
                    .order_by(ConversationMessage.sequence_number)
                )
            ).scalars().all()
        except Exception:
            msgs = []
        user_lines = [m.content.strip() for m in msgs if getattr(m, "role", None) and str(m.role) == "MessageRole.USER" and m.content and m.content.strip()]
        if user_lines:
            parsed_text = ("Önceden verilen yanıtlar baz alınarak hazırlanmış özet CV metni:\n\n" + "\n".join(user_lines))[:100000]

    # Save if we have something
    if parsed_text:
        prof.resume_text = parsed_text
        await session.commit()
        await session.refresh(cand)
    else:
        # No data available
        await session.commit()

    return cand