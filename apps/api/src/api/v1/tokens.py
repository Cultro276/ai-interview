from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from pydantic import BaseModel
import re
import unicodedata

from src.db.session import get_session
from src.db.models.candidate import Candidate
from src.api.v1.schemas import CandidateRead
from src.core.s3 import generate_presigned_put_url, generate_presigned_put_url_at_key
from src.core.metrics import collector
from src.core.config import settings


class UploadPresignRequest(BaseModel):
    token: str
    file_name: str
    content_type: str
    job_id: int | None = None


router = APIRouter(prefix="/tokens", tags=["tokens"])
class ConsentBody(BaseModel):
    token: str
    interview_id: int
    text_version: str | None = None


@router.post("/consent")
async def record_consent(body: ConsentBody, request: Request, session: AsyncSession = Depends(get_session)):
    # Validate token and interview ownership
    cand = (await session.execute(select(Candidate).where(Candidate.token == body.token))).scalar_one_or_none()
    now_utc = datetime.now(timezone.utc)
    if not cand or cand.expires_at <= now_utc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    from src.db.models.interview import Interview
    from sqlalchemy import select as _select
    interview = (
        await session.execute(_select(Interview).where(Interview.id == body.interview_id))
    ).scalar_one_or_none()
    if not interview or interview.candidate_id != cand.id:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Persist consent
    try:
        from src.db.models.consent import CandidateConsent
        ip = None
        try:
            ip = request.client.host if request and request.client else None
        except Exception:
            ip = None
        consent = CandidateConsent(candidate_id=cand.id, interview_id=interview.id, ip=ip, text_version=body.text_version)
        session.add(consent)
        await session.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/verify", response_model=CandidateRead)
async def verify_token(token: str, session: AsyncSession = Depends(get_session)):
    cand = (await session.execute(select(Candidate).where(Candidate.token == token))).scalar_one_or_none()
    now_utc = datetime.now(timezone.utc)
    # Token is valid if not expired and interview NOT completed yet.
    if not cand or cand.expires_at <= now_utc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    # If any interview for this candidate is completed, treat as used/expired
    from src.db.models.interview import Interview
    from sqlalchemy import select as _select
    completed = (
        await session.execute(
            _select(Interview).where(Interview.candidate_id == cand.id, Interview.status == "completed")
        )
    ).first()
    if completed is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview already completed")

    # Sanitize email to avoid response validation failures (old data may contain invalid emails)
    safe_email = cand.email or ""
    if "@" not in safe_email:
        safe_email = f"geçersiz+{cand.id}@example.com"

    return CandidateRead.model_validate({
        "id": cand.id,
        "user_id": cand.user_id,
        "name": cand.name,
        "email": safe_email,
        "resume_url": cand.resume_url,
        "created_at": cand.created_at,
    })


@router.post("/presign-upload")
async def presign_upload(req: UploadPresignRequest, session: AsyncSession = Depends(get_session)):
    # verify token using existing logic
    cand = (await session.execute(select(Candidate).where(Candidate.token == req.token))).scalar_one_or_none()
    now_utc = datetime.now(timezone.utc)
    # Allow presign if token not expired and interview not completed
    if not cand or cand.expires_at <= now_utc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    from src.db.models.interview import Interview
    from sqlalchemy import select as _select
    completed = (
        await session.execute(
            _select(Interview).where(Interview.candidate_id == cand.id, Interview.status == "completed")
        )
    ).first()
    if completed is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview already completed")

    # Content-type whitelist (audio/video only)
    ct = (req.content_type or "").lower()
    allowed_prefixes = ("audio/", "video/")
    if not any(ct.startswith(p) for p in allowed_prefixes):
        raise HTTPException(status_code=400, detail="Unsupported content type")

    # Build server-side file name: "{first_last}_{kind}_{YYYYMMDDHHMMSS}.{ext}"
    def slugify(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.lower()
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
        return normalized.strip("_")

    full_name = (cand.name or "candidate").strip()
    name_slug = slugify(full_name)
    kind = "audio" if req.content_type.startswith("audio") else ("video" if req.content_type.startswith("video") else "media")
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    # Try to infer extension from content_type
    ext = "webm"
    if "/mp4" in req.content_type:
        ext = "mp4"
    elif "/ogg" in req.content_type:
        ext = "ogg"
    elif "/wav" in req.content_type:
        ext = "wav"
    server_file_name = f"{name_slug}_{kind}_{ts}.{ext}"

    # Use media/{job_id}/ when provided; otherwise fall back to date-based path
    try:
        if req.job_id is not None:
            key = f"media/{req.job_id}/{server_file_name}"
            presigned = generate_presigned_put_url_at_key(key, req.content_type)
        else:
            presigned = generate_presigned_put_url(server_file_name, req.content_type, prefix="media")
        # Log only minimal presign info; avoid leaking bucket/key in prod
        try:
            import logging
            logging.getLogger(__name__).info("[S3 PRESIGN] content_type=%s", req.content_type)
        except Exception:
            pass
        # mark presign issued to measure upload duration when client later calls media PATCH
        collector.mark_presign_issued(req.token)
    except Exception as e:
        # In production (real S3), fail fast on presign errors
        raise HTTPException(status_code=500, detail=f"S3 presign failed: {str(e)}")

    return {"presigned_url": presigned["url"], "url": presigned["url"], "key": presigned["key"]}