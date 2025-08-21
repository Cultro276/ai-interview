from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from io import BytesIO
import hashlib
import os

try:
    from gtts import gTTS  # type: ignore
    _TTS_AVAILABLE = True
except Exception:
    _TTS_AVAILABLE = False


router = APIRouter(prefix="/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=800)
    lang: str = Field(default="tr")
    provider: str | None = Field(default=None, description="Force provider: 'elevenlabs' | 'azure' | 'gtts'")
    # Optional style controls
    stability: float | None = Field(default=None, ge=0, le=1)
    similarity_boost: float | None = Field(default=None, ge=0, le=1)
    style: float | None = Field(default=None, ge=0, le=1, description="ElevenLabs style strength")
    use_speaker_boost: bool | None = Field(default=None)
    # Experimental: allow inline hints like [pause], [breath]; we will sanitize for providers
    allow_inline_hints: bool | None = Field(default=False)


@router.post("/speak")
async def tts_speak(req: TTSRequest):
    from src.core.config import settings
    # If caller forces a provider, try only that and return error on failure
    def _http_error(msg: str, status: int = 502):
        from fastapi import HTTPException
        raise HTTPException(status_code=status, detail=msg)

    if req.provider == "elevenlabs":
        if not (settings.elevenlabs_api_key and settings.elevenlabs_voice_id):
            _http_error("ElevenLabs not configured")
        try:
            import requests
            # S3 cache by hash of voice+lang+text
            try:
                from src.core.s3 import object_exists, get_object_bytes, put_object_bytes
                voice_id = settings.elevenlabs_voice_id or "default"
                lang = req.lang or "tr"
                digest = hashlib.sha256((voice_id + "::" + lang + "::" + req.text).encode("utf-8")).hexdigest()
                key = f"tts/elevenlabs/{voice_id}/{lang}/{digest}.mp3"
                if settings.s3_bucket and object_exists(key):
                    body, _ = get_object_bytes(key)
                    return StreamingResponse(BytesIO(body), media_type="audio/mpeg", headers={
                        "Content-Disposition": "inline; filename=tts.mp3",
                        "Cache-Control": "public, max-age=31536000",
                        "X-TTS-Provider": "cache",
                    })
            except Exception:
                key = None

            # Optional inline hint sanitation (basic). ElevenLabs does not officially support [whisper] tags
            text = req.text
            if not req.allow_inline_hints:
                import re as _re
                text = _re.sub(r"\[(whisper|pause|breath)\]", "", text, flags=_re.I)
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": req.stability if req.stability is not None else 0.4,
                    "similarity_boost": req.similarity_boost if req.similarity_boost is not None else 0.8,
                    "style": req.style if req.style is not None else 0.5,
                    "use_speaker_boost": True if req.use_speaker_boost is None else req.use_speaker_boost,
                },
            }
            r = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}",
                json=payload,
                headers={"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
                timeout=10,
            )
            if r.status_code != 200 or not r.content:
                _http_error(f"elevenlabs_error:{r.status_code} {r.text[:200]}")
            # Save to S3 cache
            try:
                if settings.s3_bucket and key:
                    from src.core.s3 import put_object_bytes as _put
                    _put(key, r.content, "audio/mpeg")
            except Exception:
                pass
            return StreamingResponse(BytesIO(r.content), media_type="audio/mpeg", headers={
                "Content-Disposition": "inline; filename=tts.mp3",
                "Cache-Control": "public, max-age=31536000",
                "X-TTS-Provider": "elevenlabs",
            })
        except Exception as e:
            _http_error(f"elevenlabs_exception:{e}")

    if req.provider == "azure":
        if not (settings.azure_speech_key and settings.azure_speech_region):
            _http_error("Azure TTS not configured")
        try:
            import requests
            token_url = f"https://{settings.azure_speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
            tok = requests.post(token_url, headers={"Ocp-Apim-Subscription-Key": settings.azure_speech_key}, timeout=5)
            tok.raise_for_status()
            access_token = tok.text
            voice = os.getenv("AZURE_SPEECH_VOICE", "tr-TR-EmelNeural")
            ssml = f"""
<speak version='1.0' xml:lang='{req.lang}'>
  <voice name='{voice}'>
    <prosody rate='-12%' pitch='+4%'>
      {req.text}
    </prosody>
  </voice>
</speak>
""".strip()
            synth_url = f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
            r = requests.post(synth_url, data=ssml.encode("utf-8"), headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            }, timeout=10)
            if r.status_code != 200 or not r.content:
                _http_error(f"azure_error:{r.status_code} {r.text[:200]}")
            return StreamingResponse(BytesIO(r.content), media_type="audio/mpeg", headers={
                "Content-Disposition": "inline; filename=tts.mp3",
                "Cache-Control": "no-store",
                "X-TTS-Provider": "azure",
            })
        except Exception as e:
            _http_error(f"azure_exception:{e}")

    # Prefer ElevenLabs if configured (normal path)
    if settings.elevenlabs_api_key and settings.elevenlabs_voice_id:
        try:
            import requests
            voice = settings.elevenlabs_voice_id
            api_key = settings.elevenlabs_api_key
            # S3 cache
            try:
                from src.core.s3 import object_exists, get_object_bytes, put_object_bytes
                digest = hashlib.sha256((voice + "::" + (req.lang or "tr") + "::" + req.text).encode("utf-8")).hexdigest()
                key = f"tts/elevenlabs/{voice}/{req.lang or 'tr'}/{digest}.mp3"
                if settings.s3_bucket and object_exists(key):
                    body, _ = get_object_bytes(key)
                    return StreamingResponse(BytesIO(body), media_type="audio/mpeg", headers={
                        "Content-Disposition": "inline; filename=tts.mp3",
                        "Cache-Control": "public, max-age=31536000",
                        "X-TTS-Provider": "cache",
                    })
            except Exception:
                key = None

            # v1 text-to-speech
            text = req.text
            if not req.allow_inline_hints:
                import re as _re
                text = _re.sub(r"\[(whisper|pause|breath)\]", "", text, flags=_re.I)
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": req.stability if req.stability is not None else 0.4,
                    "similarity_boost": req.similarity_boost if req.similarity_boost is not None else 0.8,
                    "style": req.style if req.style is not None else 0.5,
                    "use_speaker_boost": True if req.use_speaker_boost is None else req.use_speaker_boost,
                },
            }
            r = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                json=payload,
                headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.content
            try:
                if settings.s3_bucket and key:
                    from src.core.s3 import put_object_bytes as _put
                    _put(key, data, "audio/mpeg")
            except Exception:
                pass
            return StreamingResponse(BytesIO(data), media_type="audio/mpeg", headers={
                "Content-Disposition": "inline; filename=tts.mp3",
                "Cache-Control": "public, max-age=31536000",
                "X-TTS-Provider": "elevenlabs",
            })
        except Exception:
            pass
    # Then Azure Speech if configured
    if settings.azure_speech_key and settings.azure_speech_region:
        try:
            # Minimal Azure REST call (neural voice) to synthesize MP3
            import requests  # lightweight; httpx already present but requests ok for sync here
            token_url = f"https://{settings.azure_speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
            tok = requests.post(token_url, headers={"Ocp-Apim-Subscription-Key": settings.azure_speech_key}, timeout=5)
            tok.raise_for_status()
            access_token = tok.text

            # SSML with TR voice (e.g., "tr-TR-AhmetNeural" or "tr-TR-EmelNeural")
            voice = os.getenv("AZURE_SPEECH_VOICE", "tr-TR-EmelNeural")
            ssml = f"""
<speak version='1.0' xml:lang='{req.lang}'>
  <voice name='{voice}'>
    <prosody rate='-12%' pitch='+4%'>
      {req.text}
    </prosody>
  </voice>
</speak>
""".strip()

            synth_url = f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
            r = requests.post(
                synth_url,
                data=ssml.encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                },
                timeout=10,
            )
            r.raise_for_status()
            data = r.content
            # Cache to S3 if available
            if settings.s3_bucket:
                from src.core.s3 import put_object_bytes
                digest = hashlib.sha256((req.lang + "::" + req.text).encode("utf-8")).hexdigest()
                key = f"tts/{req.lang}/{voice}/{digest}.mp3"
                put_object_bytes(key, data, "audio/mpeg")
            return StreamingResponse(BytesIO(data), media_type="audio/mpeg", headers={
                "Content-Disposition": "inline; filename=tts.mp3",
                "Cache-Control": "public, max-age=31536000",
                "X-TTS-Provider": "azure",
            })
        except Exception:
            # fall through to gTTS
            pass

    if not _TTS_AVAILABLE:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TTS engine not available")
    try:
        # If S3 available, cache by hash
        if settings.s3_bucket:
            from src.core.s3 import object_exists, get_object_bytes, put_object_bytes
            digest = hashlib.sha256((req.lang + "::" + req.text).encode("utf-8")).hexdigest()
            key = f"tts/{req.lang}/{digest}.mp3"
            if object_exists(key):
                body, _ = get_object_bytes(key)
                return StreamingResponse(BytesIO(body), media_type="audio/mpeg", headers={
                    "Content-Disposition": "inline; filename=tts.mp3",
                    "Cache-Control": "public, max-age=31536000",
                    "X-TTS-Provider": "cache",
                })
            # Generate and store
            buf = BytesIO()
            from gtts import gTTS as _gTTS  # type: ignore
            _gTTS(text=req.text, lang=req.lang, slow=False).write_to_fp(buf)
            data = buf.getvalue()
            from src.core.s3 import put_object_bytes as _put
            _put(key, data, "audio/mpeg")
            return StreamingResponse(BytesIO(data), media_type="audio/mpeg", headers={
                "Content-Disposition": "inline; filename=tts.mp3",
                "Cache-Control": "public, max-age=31536000",
            })

        # Fallback: in-memory generation without cache
        buf = BytesIO()
        from gtts import gTTS as _gTTS  # type: ignore
        _gTTS(text=req.text, lang=req.lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        headers = {
            "Content-Disposition": "inline; filename=tts.mp3",
            "Cache-Control": "no-store",
        }
        headers["X-TTS-Provider"] = "gtts"
        return StreamingResponse(buf, media_type="audio/mpeg", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


