from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from pydantic import BaseModel
import re
import unicodedata

from src.db.session import get_session
from src.db.models.candidate import Candidate
from src.api.v1.schemas import CandidateRead
from src.core.s3 import generate_presigned_put_url
from src.core.metrics import collector
from src.core.config import settings


class UploadPresignRequest(BaseModel):
    token: str
    file_name: str
    content_type: str


router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.post("/verify", response_model=CandidateRead)
async def verify_token(token: str, session: AsyncSession = Depends(get_session)):
    cand = (await session.execute(select(Candidate).where(Candidate.token == token))).scalar_one_or_none()
    now_utc = datetime.now(timezone.utc)
    if not cand or cand.expires_at <= now_utc or cand.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    # Sanitize email to avoid response validation failures (old data may contain invalid emails)
    safe_email = cand.email or ""
    if "@" not in safe_email:
        safe_email = f"invalid+{cand.id}@example.com"

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
    # Single-use enforcement: if token already used (interview completed), block new uploads
    if not cand or cand.expires_at <= now_utc or cand.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

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

    # Use separate S3 prefix for interview media, not uploads
    # We encode the filename into the key via generate_presigned_put_url (which currently defaults to uploads/)
    # Adjust by passing a server_file_name that will be prefixed in s3.py with uploads/. We will later move media to "media/" if needed.
    # Use separate prefix for interview media
    try:
        presigned = generate_presigned_put_url(server_file_name, req.content_type, prefix="media")
        print(f"[S3 PRESIGN] bucket={settings.s3_bucket} key={presigned['key']} content_type={req.content_type}")
        # mark presign issued to measure upload duration when client later calls media PATCH
        collector.mark_presign_issued(req.token)
    except Exception as e:
        # Smooth dev fallback: return localhost fake URL to avoid hard failures when S3 is not configured
        fake_key = f"media/dev/{server_file_name}"
        fake_url = f"http://localhost:8000/dev-upload/{fake_key}"
        print(f"[S3 PRESIGN:FALLBACK] {e} → using {fake_url}")
        return {"presigned_url": fake_url, "url": fake_url, "key": fake_key}

    return {"presigned_url": presigned["url"], "url": presigned["url"], "key": presigned["key"]}