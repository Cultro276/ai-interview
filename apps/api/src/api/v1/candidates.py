from typing import List
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

from src.auth import current_active_user, get_effective_owner_id, ensure_permission
from src.db.models.user import User
from src.api.v1.schemas import CandidateCreate, CandidateRead, CandidateUpdate
from src.api.v1.enhanced_schemas import SecureCandidateCreate, EnhancedErrorResponse
from src.core.security import SecurityAuditLogger
from src.core.s3 import generate_presigned_get_url
from src.db.models.candidate_profile import CandidateProfile
from src.db.models.conversation import ConversationMessage
from src.db.models.interview import Interview
from src.services.nlp import parse_resume_bytes
from src.services.nlp import summarize_candidate_profile
from sqlalchemy import select as _select
import httpx
from src.core.mail import send_email_resend
from urllib.parse import urlparse
from src.db.models.candidate import Candidate
from src.db.session import get_session

router = APIRouter(prefix="/candidates", tags=["candidates"])


# --- Helpers: normalization for phone and LinkedIn ---
def _norm_phone(v: str | None) -> str | None:
    if not v:
        return None
    import re as _re
    digits = _re.sub(r"[^\d+]", "", v)
    if digits.startswith("+90") and len(digits) >= 12:
        return digits
    if digits.startswith("90") and len(digits) >= 11:
        return "+" + digits
    if digits.startswith("0") and len(digits) >= 11:
        return "+90" + digits[1:]
    if digits.startswith("5") and len(digits) >= 10:
        return "+90" + digits
    return digits[:20]


def _norm_linkedin(u: str | None) -> str | None:
    if not u:
        return None
    u = u.strip()
    low = u.lower()
    if low.startswith("http://") or low.startswith("https://"):
        pass
    else:
        if low.startswith("in/") or low.startswith("company/"):
            u = "https://www.linkedin.com/" + u
        else:
            u = "https://www.linkedin.com/in/" + u
    return u


@router.get("/", response_model=List[CandidateRead])
async def list_candidates(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    owner_id = get_effective_owner_id(current_user)
    try:
        result = await session.execute(select(Candidate).where(Candidate.user_id == owner_id))
        rows: List[Candidate] = list(result.scalars().all())
    except Exception as e:
        # Handle encryption/decryption errors gracefully
        import logging
        logging.error(f"Database query failed: {e}")
        # Return empty list for now to prevent crashes
        return []
    # Sanitize potentially invalid emails to avoid 500 due to response model validation
    safe_list: List[CandidateRead] = []
    for cand in rows:
        email_value = cand.email or ""
        if "@" not in email_value:
            email_value = f"geçersiz+{cand.id}@example.com"
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
    ensure_permission(current_user, manage_candidates=True)
    candidate_data = candidate_in.dict(exclude={'expires_in_days'})
    # Normalize phone and LinkedIn
    def _norm_phone(v: str | None) -> str | None:
        if not v:
            return None
        import re as _re
        digits = _re.sub(r"[^\d+]", "", v)
        # Basic TR normalization: start with +90 or 0/5… assume mobile
        if digits.startswith("+90") and len(digits) >= 12:
            return digits
        if digits.startswith("90") and len(digits) >= 11:
            return "+" + digits
        if digits.startswith("0") and len(digits) >= 11:
            return "+90" + digits[1:]
        if digits.startswith("5") and len(digits) >= 10:
            return "+90" + digits
        return digits[:20]
    def _norm_linkedin(u: str | None) -> str | None:
        if not u:
            return None
        u = u.strip()
        low = u.lower()
        if low.startswith("http://") or low.startswith("https://"):
            pass
        else:
            # accept bare handle like in/username
            if low.startswith("in/") or low.startswith("company/"):
                u = "https://www.linkedin.com/" + u
            else:
                u = "https://www.linkedin.com/in/" + u
        return u
    if 'phone' in candidate_data:
        candidate_data['phone'] = _norm_phone(candidate_data.get('phone'))
    if 'linkedin_url' in candidate_data:
        candidate_data['linkedin_url'] = _norm_linkedin(candidate_data.get('linkedin_url'))
    candidate = Candidate(**candidate_data, user_id=get_effective_owner_id(current_user))
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
    ensure_permission(current_user, manage_candidates=True)
    owner_id = get_effective_owner_id(current_user)
    cand = (await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == owner_id))).scalar_one_or_none()
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
    ensure_permission(current_user, manage_candidates=True)
    owner_id = get_effective_owner_id(current_user)
    cand = (
        await session.execute(
            select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == owner_id)
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
    owner_id = get_effective_owner_id(current_user)
    cand = (await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == owner_id))).scalar_one_or_none()
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
    owner_id = get_effective_owner_id(current_user)
    cand = (await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == owner_id))).scalar_one_or_none()
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
        # Force inline for doc/docx where possible
        content_hint = None
        if key.lower().endswith(".docx"):
            content_hint = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        url = generate_presigned_get_url(
            key,
            expires=expires_in,
            response_content_disposition="inline",
            response_content_type=content_hint,
        )
        return {"url": url}
    # If value looks like an S3 key (contains '/'), presign directly; add response-content-type for inline preview of docx
    if "/" in ru and not ru.startswith("http"):
        # Suggest inline rendering via response headers
        content_hint = None
        if ru.lower().endswith(".docx"):
            content_hint = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        url = generate_presigned_get_url(
            ru.lstrip("/"),
            expires=expires_in,
            response_content_disposition="inline",
            response_content_type=content_hint,
        )
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
    ensure_permission(current_user, manage_candidates=True)
    owner_id = get_effective_owner_id(current_user)
    cand = (await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == owner_id))).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    # Apply updates with normalization
    upd = cand_in.dict(exclude_unset=True)
    if 'phone' in upd:
        upd['phone'] = _norm_phone(upd.get('phone'))
    if 'linkedin_url' in upd:
        upd['linkedin_url'] = _norm_linkedin(upd.get('linkedin_url'))
    for field, value in upd.items():
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
    ensure_permission(current_user, manage_candidates=True)
    owner_id = get_effective_owner_id(current_user)
    cand = (await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == owner_id))).scalar_one_or_none()
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
        # Fill parsed_json with smart extractor
        try:
            from src.services.nlp import extract_candidate_fields_smart
            import json as _json
            fields = await extract_candidate_fields_smart(parsed_text, cand.resume_url)
            prof.parsed_json = _json.dumps(fields, ensure_ascii=False)
            # Optionally update candidate name/email when confidently extracted
            if isinstance(fields, dict):
                new_name = fields.get("name")
                new_email = fields.get("email")
                if isinstance(new_name, str) and new_name.strip():
                    cand.name = new_name.strip()[:255]
                if isinstance(new_email, str) and new_email and "@" in new_email:
                    # ensure uniqueness
                    exists = (
                        await session.execute(select(Candidate.id).where(Candidate.email == new_email, Candidate.id != cand.id))
                    ).scalar_one_or_none()
                    if exists is None:
                        cand.email = new_email.strip()
        except Exception:
            pass
        await session.commit()
        await session.refresh(cand)
    else:
        # No data available
        await session.commit()

    return cand


# --- Candidate profile (parsed fields + resume text) ---


class CandidateProfileRead(BaseModel):
    resume_text: str | None = None
    parsed: dict | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None


@router.get("/{cand_id}/profile", response_model=CandidateProfileRead)
async def get_candidate_profile(
    cand_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    owner_id = get_effective_owner_id(current_user)
    cand = (
        await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == owner_id))
    ).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    prof = (
        await session.execute(_select(CandidateProfile).where(CandidateProfile.candidate_id == cand.id))
    ).scalar_one_or_none()
    if not prof:
        return CandidateProfileRead()
    parsed_obj: dict | None = None
    try:
        import json as _json
        parsed_obj = _json.loads(prof.parsed_json) if prof.parsed_json else None
    except Exception:
        parsed_obj = None
    links = (parsed_obj or {}).get("links") if isinstance(parsed_obj, dict) else None
    phone_val = (parsed_obj or {}).get("phone") if isinstance(parsed_obj, dict) else None
    if not phone_val:
        try:
            phone_val = getattr(cand, "phone", None)
        except Exception:
            phone_val = None
    linkedin_val = (links or {}).get("linkedin") if isinstance(links, dict) else None
    if not linkedin_val:
        try:
            linkedin_val = getattr(cand, "linkedin_url", None)
        except Exception:
            linkedin_val = None
    return CandidateProfileRead(
        resume_text=prof.resume_text,
        parsed=parsed_obj or None,
        phone=phone_val,
        linkedin=linkedin_val,
        github=(links or {}).get("github") if isinstance(links, dict) else None,
        website=(links or {}).get("website") if isinstance(links, dict) else None,
    )


# --- CV summary (LLM if available, fallback empty string) ---


class CandidateCvSummary(BaseModel):
    summary: str = ""


@router.get("/{cand_id}/cv-summary", response_model=CandidateCvSummary)
async def get_candidate_cv_summary(
    cand_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    owner_id = get_effective_owner_id(current_user)
    cand = (
        await session.execute(select(Candidate).where(Candidate.id == cand_id, Candidate.user_id == owner_id))
    ).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    # resume text
    prof = (
        await session.execute(_select(CandidateProfile).where(CandidateProfile.candidate_id == cand.id))
    ).scalar_one_or_none()
    resume_text = prof.resume_text if prof and getattr(prof, "resume_text", None) else ""
    # If no resume_text but a resume_url exists, fetch and parse on-demand
    if (not resume_text) and cand.resume_url and cand.resume_url.strip():
        try:
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
                    resume_text = parse_resume_bytes(resp.content, resp.headers.get("Content-Type"), cand.resume_url)
                    # persist resume_text for future calls
                    if resume_text:
                        if not prof:
                            prof = CandidateProfile(candidate_id=cand.id)
                            session.add(prof)
                            await session.flush()
                        prof.resume_text = resume_text[:100000]
                        await session.commit()
        except Exception:
            resume_text = resume_text or ""
    # Check cached summary inside parsed_json
    cached: str | None = None
    if prof and getattr(prof, "parsed_json", None):
        try:
            import json as _json
            obj = _json.loads(prof.parsed_json or "{}")
            if isinstance(obj, dict):
                cached = obj.get("cv_summary") if isinstance(obj.get("cv_summary"), str) else None
        except Exception:
            cached = None
    if cached:
        return CandidateCvSummary(summary=cached)
    # job description from latest interview (if any)
    job_desc = None
    try:
        latest_interview = (
            await session.execute(
                _select(Interview).where(Interview.candidate_id == cand.id).order_by(Interview.id.desc())
            )
        ).scalars().first()
        if latest_interview:
            from src.db.models.job import Job  # local import
            j = (await session.execute(_select(Job).where(Job.id == latest_interview.job_id))).scalar_one_or_none()
            if j and getattr(j, "description", None):
                job_desc = j.description
    except Exception:
        job_desc = None
    # summarize
    try:
        summary = await summarize_candidate_profile(resume_text or "", job_desc)
    except Exception:
        summary = ""
    # persist inside parsed_json for next calls
    if prof:
        try:
            import json as _json
            obj = {}
            if prof.parsed_json:
                try:
                    obj = _json.loads(prof.parsed_json) or {}
                except Exception:
                    obj = {}
            obj["cv_summary"] = summary or ""
            prof.parsed_json = _json.dumps(obj, ensure_ascii=False)
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
    return CandidateCvSummary(summary=summary or "")