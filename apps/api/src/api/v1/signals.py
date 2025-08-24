from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from src.db.session import get_session
from src.db.models.candidate import Candidate
from src.db.models.interview import Interview
from src.db.models.interview_signal import InterviewSignal


router = APIRouter(prefix="/signals", tags=["signals"])


class SignalCreate(BaseModel):
    token: str
    interview_id: int
    kind: str
    meta: str | None = None


@router.post("/public", status_code=status.HTTP_201_CREATED)
async def create_public_signal(body: SignalCreate, session: AsyncSession = Depends(get_session)):
    # validate token & interview
    cand = (await session.execute(select(Candidate).where(Candidate.token == body.token))).scalar_one_or_none()
    now_utc = datetime.now(timezone.utc)
    if not cand or cand.expires_at <= now_utc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    interview = (await session.execute(select(Interview).where(Interview.id == body.interview_id))).scalar_one_or_none()
    if not interview or interview.candidate_id != cand.id:
        raise HTTPException(status_code=404, detail="Interview not found")
    sig = InterviewSignal(interview_id=interview.id, kind=body.kind[:50], meta=(body.meta or None))
    session.add(sig)
    await session.commit()
    return {"ok": True}


