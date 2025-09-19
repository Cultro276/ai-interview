from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.db.models.candidate import Candidate
from src.core.gdpr import gdpr_manager
from src.core.config import settings


router = APIRouter(prefix="/gdpr", tags=["gdpr"])


class GdprExportRequest(BaseModel):
    email: str | None = None
    token: str | None = None
    format: Literal["json", "zip"] = "json"


async def _resolve_email(session: AsyncSession, *, email: str | None, token: str | None) -> str:
    if email and email.strip():
        return email.strip().lower()
    if (token or "").strip():
        cand = (
            await session.execute(select(Candidate).where(Candidate.token == token))
        ).scalar_one_or_none()
        if not cand:
            raise HTTPException(status_code=404, detail="Candidate not found")
        # Optional expiry check
        try:
            from datetime import datetime, timezone
            if cand.expires_at and cand.expires_at <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="Token expired")
        except Exception:
            pass
        # Candidate email may be encrypted; SQLAlchemy type handles decrypt on access
        if not cand.email:
            raise HTTPException(status_code=400, detail="Email unavailable for candidate")
        return cand.email.lower()
    raise HTTPException(status_code=400, detail="Provide email or token")


@router.post("/export")
async def export_personal_data(body: GdprExportRequest, session: AsyncSession = Depends(get_session)):
    subject_email = await _resolve_email(session, email=body.email, token=body.token)
    try:
        data = await gdpr_manager.export_personal_data(subject_email, format_type=body.format)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")
    if body.format == "json":
        return Response(content=data, media_type="application/json")
    # zip
    headers = {"Content-Disposition": "attachment; filename=gdpr_export.zip"}
    return StreamingResponse(iter([data]), media_type="application/zip", headers=headers)


class GdprEraseRequest(BaseModel):
    email: str | None = None
    token: str | None = None
    reason: str | None = None
    admin_secret: str | None = None


@router.post("/erase")
async def erase_personal_data(body: GdprEraseRequest, session: AsyncSession = Depends(get_session)):
    # Authorization: either candidate token flow or admin secret
    is_admin = bool(body.admin_secret and body.admin_secret == settings.internal_admin_secret)
    if not is_admin and not (body.token and body.token.strip()):
        raise HTTPException(status_code=401, detail="Authorization required (token or admin_secret)")
    subject_email = await _resolve_email(session, email=body.email, token=body.token)
    try:
        req_id = await gdpr_manager.submit_erasure_request(subject_email, body.reason or "self-serve")
        ok = await gdpr_manager.process_erasure_request(req_id)
        return {"ok": bool(ok), "request_id": req_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erasure failed: {e}")


