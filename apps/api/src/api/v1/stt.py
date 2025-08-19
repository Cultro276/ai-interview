from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.services.stt import transcribe_with_whisper


router = APIRouter(prefix="/stt", tags=["stt"])


class STTRequest(BaseModel):
    interview_id: int
    audio_url: str | None = None


@router.post("/transcribe-file")
async def stt_transcribe_file(interview_id: int, file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    try:
        data = await file.read()
        text = await transcribe_with_whisper(data, file.content_type or "audio/webm")
        if not text:
            raise HTTPException(status_code=502, detail="STT provider returned empty transcript")
        # Save transcript via existing endpoint logic (in-memory stub for now)
        from .interviews import upload_transcript, TranscriptPayload  # reuse
        payload = TranscriptPayload(text=text, provider="whisper")
        await upload_transcript(interview_id, payload, session)
        return {"interview_id": interview_id, "length": len(text)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


