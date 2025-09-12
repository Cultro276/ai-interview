from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from io import BytesIO
import httpx
import os
from anyio import to_thread

try:
    from gtts import gTTS  # type: ignore
    _TTS_AVAILABLE = True
except Exception:
    _TTS_AVAILABLE = False


router = APIRouter(prefix="/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=800)
    lang: str = Field(default="tr")
    provider: str | None = Field(default=None, description="Force provider: 'openai' | 'azure' | 'gtts' | 'elevenlabs'")
    stability: float | None = Field(default=None, ge=0, le=1)
    similarity_boost: float | None = Field(default=None, ge=0, le=1)
    style: float | None = Field(default=None, ge=0, le=1)
    use_speaker_boost: bool | None = Field(default=None)
    preset: str | None = Field(default=None)


@router.post("/speak")
async def tts_speak(req: TTSRequest):
    from src.core.config import settings

    def _http_error(msg: str, status: int = 502):
        raise HTTPException(status_code=status, detail=msg)

    def _azure_ssml(text: str) -> str:
        # Natural Turkish corporate tone with light prosody
        rate = "+4%" if (req.preset or "").lower() == "corporate" else "+7%"
        pitch = "+1%"
        voice = os.getenv("AZURE_SPEECH_VOICE", "tr-TR-EmelNeural")
        import re as _re
        def _inject_pauses(t: str) -> str:
            t = t.strip()
            t = _re.sub(r"([.!?])\s+", r"\1 <break time='150ms'/> ", t)
            return t
        body = _inject_pauses(text)
        return f"""
<speak version='1.0' xml:lang='{req.lang}'>
  <voice name='{voice}'>
    <prosody rate='{rate}' pitch='{pitch}'>
      <mstts:express-as style='calm'>
        {body}
      </mstts:express-as>
    </prosody>
  </voice>
</speak>
""".strip()

    # 1. OPENAI TTS
    if req.provider == "openai" or (
        not req.provider and settings.openai_api_key
    ):
        try:
            # Use httpx client to stream audio to avoid type issues in some linters
            headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
            voice = os.getenv("OPENAI_TTS_VOICE", "coral")

            async def _generate():
                payload = {
                    "model": "tts-1",
                    "voice": voice,
                    "input": req.text,
                }
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/audio/speech",
                        json=payload,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    # Stream in chunks to the client
                    chunk = resp.content
                    yield chunk

            return StreamingResponse(
                _generate(),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=tts.mp3",
                    "Cache-Control": "no-store",
                    "X-TTS-Provider": "openai",
                },
            )
        except Exception as e:
            if req.provider == "openai":
                _http_error(f"openai_tts_exception:{e}")
            import logging
            logging.warning(f"OpenAI TTS failed: {e}")

    # 2. AZURE TTS
    if req.provider == "azure" or (
        not req.provider and settings.azure_speech_key and settings.azure_speech_region
    ):
        try:
            token_url = f"https://{settings.azure_speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
            async with httpx.AsyncClient(timeout=3.0) as client:
                tok = await client.post(
                    token_url,
                    headers={"Ocp-Apim-Subscription-Key": str(settings.azure_speech_key or "")},
                )
                tok.raise_for_status()
                access_token = tok.text

            ssml = _azure_ssml(req.text)
            synth_url = f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    synth_url,
                    content=ssml.encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/ssml+xml",
                        # HD-quality mono MP3 for clear voice with manageable size
                        "X-Microsoft-OutputFormat": "audio-48khz-96kbitrate-mono-mp3",
                    },
                )
            if r.status_code != 200 or not r.content:
                _http_error(f"azure_error:{r.status_code} {r.text[:200]}")
            return StreamingResponse(
                BytesIO(r.content),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=tts.mp3",
                    "Cache-Control": "no-store",
                    "X-TTS-Provider": "azure",
                },
            )
        except Exception as e:
            if req.provider == "azure":
                _http_error(f"azure_exception:{e}")
            import logging
            logging.warning(f"Azure TTS failed: {e}")

    # 3. GTTS
    if req.provider == "gtts" or (not req.provider and _TTS_AVAILABLE):
        try:
            buf = BytesIO()
            from gtts import gTTS as _gTTS  # type: ignore
            import asyncio

            def _make_gtts():
                _gTTS(text=req.text, lang=req.lang, slow=False).write_to_fp(buf)

            await asyncio.wait_for(to_thread.run_sync(_make_gtts), timeout=8.0)
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=tts.mp3",
                    "Cache-Control": "public, max-age=31536000",
                    "X-TTS-Provider": "gtts",
                },
            )
        except Exception as e:
            if req.provider == "gtts":
                _http_error(f"gtts_exception:{e}")
            import logging
            logging.warning(f"gTTS failed: {e}")

    # 4. ELEVENLABS (son fallback)
    if req.provider == "elevenlabs" or (
        not req.provider and settings.elevenlabs_api_key and settings.elevenlabs_voice_id
    ):
        try:
            payload = {
                "text": req.text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": req.stability if req.stability is not None else 0.6,
                    "similarity_boost": req.similarity_boost if req.similarity_boost is not None else 0.7,
                    "style": req.style if req.style is not None else 0.3,
                    "use_speaker_boost": True if req.use_speaker_boost is None else req.use_speaker_boost,
                },
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}",
                    json=payload,
                    headers={
                        "xi-api-key": str(settings.elevenlabs_api_key or ""),
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg",
                    },
                )
            if r.status_code != 200 or not r.content:
                _http_error(f"elevenlabs_error:{r.status_code} {r.text[:200]}")
            return StreamingResponse(
                BytesIO(r.content),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=tts.mp3",
                    "Cache-Control": "public, max-age=31536000",
                    "X-TTS-Provider": "elevenlabs",
                },
            )
        except Exception as e:
            if req.provider == "elevenlabs":
                _http_error(f"elevenlabs_exception:{e}")
            import logging
            logging.warning(f"ElevenLabs TTS failed: {e}")

    # Fallback silence
    empty_mp3 = b"\xff\xfb\x90\x00" + b"\x00" * 100
    return StreamingResponse(
        BytesIO(empty_mp3),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=silence.mp3",
            "Cache-Control": "no-store",
            "X-TTS-Provider": "error-fallback",
        }
    )
