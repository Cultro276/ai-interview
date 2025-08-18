from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from io import BytesIO

try:
    from gtts import gTTS  # type: ignore
    _TTS_AVAILABLE = True
except Exception:
    _TTS_AVAILABLE = False


router = APIRouter(prefix="/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=800)
    lang: str = Field(default="tr")


@router.post("/speak")
async def tts_speak(req: TTSRequest):
    if not _TTS_AVAILABLE:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TTS engine not available")
    try:
        # Generate MP3 in-memory
        buf = BytesIO()
        gTTS(text=req.text, lang=req.lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        headers = {
            "Content-Disposition": "inline; filename=tts.mp3",
            "Cache-Control": "no-store",
        }
        return StreamingResponse(buf, media_type="audio/mpeg", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


