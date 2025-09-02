from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from io import BytesIO
import hashlib
import os
import httpx
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
    provider: str | None = Field(default=None, description="Force provider: 'elevenlabs' | 'azure' | 'gtts'")
    # Optional style controls
    stability: float | None = Field(default=None, ge=0, le=1)
    similarity_boost: float | None = Field(default=None, ge=0, le=1)
    style: float | None = Field(default=None, ge=0, le=1, description="ElevenLabs style strength")
    use_speaker_boost: bool | None = Field(default=None)
    # Experimental: allow inline hints like [pause], [breath]; we will sanitize for providers
    allow_inline_hints: bool | None = Field(default=False)
    # Preset: if set to 'corporate', enforce neutral/professional tone
    preset: str | None = Field(default=None, description="'corporate' for neutral, professional tone")


@router.post("/speak")
async def tts_speak(req: TTSRequest):
    from src.core.config import settings
    # If caller forces a provider, try only that and return error on failure
    def _http_error(msg: str, status: int = 502):
        from fastapi import HTTPException
        raise HTTPException(status_code=status, detail=msg)

    def _apply_preset_voice_settings(_defaults: dict) -> dict:
        if (req.preset or "").lower() == "corporate":
            return {
                "stability": req.stability if req.stability is not None else 0.7,
                "similarity_boost": req.similarity_boost if req.similarity_boost is not None else 0.65,
                "style": req.style if req.style is not None else 0.2,
                "use_speaker_boost": True if req.use_speaker_boost is None else req.use_speaker_boost,
            }
        return _defaults

    def _azure_ssml(text: str) -> str:
        """Humanized SSML: slight speed-up, neutral pitch, micro-pauses between clauses.

        We avoid overusing pauses; keep them short to sound natural.
        """
        rate = "+2%" if (req.preset or "").lower() == "corporate" else "+6%"
        pitch = "+0%"
        voice = os.getenv("AZURE_SPEECH_VOICE", "tr-TR-EmelNeural")
        # Insert short breaks after sentence boundaries.
        import re as _re
        def _inject_pauses(t: str) -> str:
            t = t.strip()
            t = _re.sub(r"([.!?])\s+", r"\\1 <break time='150ms'/> ", t)
            return t
        body = _inject_pauses(text)
        return f"""
<speak version='1.0' xml:lang='{req.lang}'>
  <voice name='{voice}'>
    <prosody rate='{rate}' pitch='{pitch}'>
      {body}
    </prosody>
  </voice>
</speak>
""".strip()

    if req.provider == "elevenlabs":
        if not (settings.elevenlabs_api_key and settings.elevenlabs_voice_id):
            _http_error("ElevenLabs not configured")
        try:
            # S3 cache by hash of voice+lang+text
            try:
                from src.core.s3 import object_exists, get_object_bytes
                voice_id = settings.elevenlabs_voice_id or "default"
                lang = req.lang or "tr"
                digest = hashlib.sha256((voice_id + "::" + lang + "::" + req.text).encode("utf-8")).hexdigest()
                key = f"tts/elevenlabs/{voice_id}/{lang}/{digest}.mp3"
                if settings.s3_bucket and await to_thread.run_sync(object_exists, key):
                    body, _ = await to_thread.run_sync(get_object_bytes, key)
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
                "voice_settings": _apply_preset_voice_settings({
                    "stability": req.stability if req.stability is not None else 0.6,
                    "similarity_boost": req.similarity_boost if req.similarity_boost is not None else 0.7,
                    "style": req.style if req.style is not None else 0.3,
                    "use_speaker_boost": True if req.use_speaker_boost is None else req.use_speaker_boost,
                }),
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}",
                    json=payload,
                    headers={"xi-api-key": str(settings.elevenlabs_api_key or ""), "Content-Type": "application/json", "Accept": "audio/mpeg"},
                )
            if r.status_code != 200 or not r.content:
                _http_error(f"elevenlabs_error:{r.status_code} {r.text[:200]}")
            # Save to S3 cache
            try:
                if settings.s3_bucket and key:
                    from src.core.s3 import put_object_bytes as _put
                    await to_thread.run_sync(_put, key, r.content, "audio/mpeg")
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
            token_url = f"https://{settings.azure_speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
            async with httpx.AsyncClient(timeout=5.0) as client:
                tok = await client.post(token_url, headers={"Ocp-Apim-Subscription-Key": str(settings.azure_speech_key or "")})
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
                        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                    },
                )
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
            voice = settings.elevenlabs_voice_id
            api_key = settings.elevenlabs_api_key
            # S3 cache
            try:
                from src.core.s3 import object_exists, get_object_bytes
                digest = hashlib.sha256((voice + "::" + (req.lang or "tr") + "::" + req.text).encode("utf-8")).hexdigest()
                key = f"tts/elevenlabs/{voice}/{req.lang or 'tr'}/{digest}.mp3"
                if settings.s3_bucket and await to_thread.run_sync(object_exists, key):
                    body, _ = await to_thread.run_sync(get_object_bytes, key)
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
                    "stability": req.stability if req.stability is not None else 0.6,
                    "similarity_boost": req.similarity_boost if req.similarity_boost is not None else 0.7,
                    "style": req.style if req.style is not None else 0.3,
                    "use_speaker_boost": True if req.use_speaker_boost is None else req.use_speaker_boost,
                },
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                    json=payload,
                    headers={"xi-api-key": str(api_key or ""), "Content-Type": "application/json", "Accept": "audio/mpeg"},
                )
                r.raise_for_status()
            data = r.content
            try:
                if settings.s3_bucket and key:
                    from src.core.s3 import put_object_bytes as _put
                    await to_thread.run_sync(_put, key, data, "audio/mpeg")
            except Exception:
                pass
            return StreamingResponse(BytesIO(data), media_type="audio/mpeg", headers={
                "Content-Disposition": "inline; filename=tts.mp3",
                "Cache-Control": "public, max-age=31536000",
                "X-TTS-Provider": "elevenlabs",
            })
        except Exception as e:
            # Log ElevenLabs failure and continue to next provider
            import logging
            logging.warning(f"ElevenLabs TTS failed: {e}")
            pass
    # Then Azure Speech if configured
    if settings.azure_speech_key and settings.azure_speech_region:
        try:
            # Minimal Azure REST call (neural voice) to synthesize MP3
            token_url = f"https://{settings.azure_speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
            async with httpx.AsyncClient(timeout=5.0) as client:
                tok = await client.post(token_url, headers={"Ocp-Apim-Subscription-Key": settings.azure_speech_key})
                tok.raise_for_status()
                access_token = tok.text

            # SSML with TR voice (e.g., "tr-TR-AhmetNeural" or "tr-TR-EmelNeural")
            ssml = _azure_ssml(req.text)

            synth_url = f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    synth_url,
                    content=ssml.encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/ssml+xml",
                        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                    },
                )
                r.raise_for_status()
            data = r.content
            # Cache to S3 if available
            if settings.s3_bucket:
                from src.core.s3 import put_object_bytes
                digest = hashlib.sha256((req.lang + "::" + req.text).encode("utf-8")).hexdigest()
                # voice variable is inside _azure_ssml; use env voice for cache path
                cache_voice = os.getenv("AZURE_SPEECH_VOICE", "tr-TR-EmelNeural")
                key = f"tts/{req.lang}/{cache_voice}/{digest}.mp3"
                await to_thread.run_sync(put_object_bytes, key, data, "audio/mpeg")
            return StreamingResponse(BytesIO(data), media_type="audio/mpeg", headers={
                "Content-Disposition": "inline; filename=tts.mp3",
                "Cache-Control": "public, max-age=31536000",
                "X-TTS-Provider": "azure",
            })
        except Exception as e:
            # Log Azure TTS failure and fall through to gTTS
            import logging
            logging.warning(f"Azure TTS failed: {e}")
            pass

    if not _TTS_AVAILABLE:
        # Return empty audio response instead of error to prevent interview from getting stuck
        empty_mp3 = b'\xff\xfb\x90\x00' + b'\x00' * 100  # Minimal valid MP3 header
        return StreamingResponse(BytesIO(empty_mp3), media_type="audio/mpeg", headers={
            "Content-Disposition": "inline; filename=silence.mp3",
            "Cache-Control": "no-store",
            "X-TTS-Provider": "fallback-silence",
        })
    try:
        # If S3 available, cache by hash
        if settings.s3_bucket:
            from src.core.s3 import object_exists, get_object_bytes, put_object_bytes
            digest = hashlib.sha256((req.lang + "::" + req.text).encode("utf-8")).hexdigest()
            key = f"tts/{req.lang}/{digest}.mp3"
            if await to_thread.run_sync(object_exists, key):
                body, _ = await to_thread.run_sync(get_object_bytes, key)
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
            await to_thread.run_sync(_put, key, data, "audio/mpeg")
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
        # Return silent audio instead of error to prevent interview from getting stuck
        import logging
        logging.warning(f"TTS fallback failed: {e}")
        empty_mp3 = b'\xff\xfb\x90\x00' + b'\x00' * 100  # Minimal valid MP3 header
        return StreamingResponse(BytesIO(empty_mp3), media_type="audio/mpeg", headers={
            "Content-Disposition": "inline; filename=silence.mp3",
            "Cache-Control": "no-store",
            "X-TTS-Provider": "error-fallback",
        })



@router.post("/stream-speak")
async def tts_stream_speak(req: TTSRequest):
    """Stream ElevenLabs TTS audio in real-time using chunked transfer.

    This proxies ElevenLabs HTTP streaming so the client can begin playback immediately.
    """
    from src.core.config import settings
    if not (settings.elevenlabs_api_key and settings.elevenlabs_voice_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ElevenLabs not configured")

    # Optional inline hint sanitation
    text = req.text
    if not req.allow_inline_hints:
        import re as _re
        text = _re.sub(r"\[(whisper|pause|breath)\]", "", text, flags=_re.I)

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": req.stability if req.stability is not None else 0.6,
            "similarity_boost": req.similarity_boost if req.similarity_boost is not None else 0.7,
            "style": req.style if req.style is not None else 0.3,
            "use_speaker_boost": True if req.use_speaker_boost is None else req.use_speaker_boost,
        },
    }

    headers = {
        "xi-api-key": str(settings.elevenlabs_api_key or ""),
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    async def _generate():
        async with httpx.AsyncClient(timeout=None) as client:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    # Read small text body for error context (best-effort)
                    try:
                        detail = (await resp.aread()).decode(errors="ignore")[:200]
                    except Exception:
                        detail = ""
                    raise HTTPException(status_code=502, detail=f"elevenlabs_stream_error:{resp.status_code} {detail}")
                async for chunk in resp.aiter_bytes():
                    if chunk:
                        yield chunk

    return StreamingResponse(_generate(), media_type="audio/mpeg", headers={
        "Content-Disposition": "inline; filename=tts.mp3",
        "Cache-Control": "no-store",
        "X-TTS-Provider": "elevenlabs-stream",
    })

