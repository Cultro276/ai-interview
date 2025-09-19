from __future__ import annotations

import io
from typing import Optional

import httpx

from src.core.config import settings
from anyio import to_thread
import base64
import asyncio
import os


async def transcribe_with_whisper(audio_bytes: bytes, content_type: str = "audio/webm") -> str:
    """Send audio to OpenAI Whisper API if OPENAI_API_KEY is configured.

    Falls back to empty string on failure so the caller can decide next steps.
    """
    # Debug logs kept minimal to avoid leaking sensitive info in production
    print(f"[STT DEBUG] API key configured: {bool(settings.openai_api_key)}")
    
    if not settings.openai_api_key:
        print("[STT DEBUG] No OpenAI API key found")
        return ""
    try:
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
        }
        form = {
            "model": "whisper-1",
        }
        # OpenAI desteklediği içerik tipleri: flac, m4a, mp3, mp4, mpeg, mpga, oga, ogg, wav, webm
        # Dosya uzantısını içerik tipine göre doğru verelim
        ct = (content_type or "audio/webm").lower()
        if "mp4" in ct:
            filename = "audio.mp4"
            send_ct = "audio/mp4"
        elif "mpeg" in ct or "mpga" in ct or "mp3" in ct:
            filename = "audio.mp3"
            send_ct = "audio/mpeg"
        elif "ogg" in ct or "oga" in ct:
            filename = "audio.ogg"
            send_ct = "audio/ogg"
        elif "wav" in ct:
            filename = "audio.wav"
            send_ct = "audio/wav"
        elif "flac" in ct:
            filename = "audio.flac"
            send_ct = "audio/flac"
        else:
            filename = "audio.webm"
            send_ct = "audio/webm"

        files = {
            "file": (filename, io.BytesIO(audio_bytes), send_ct),
        }
        # Avoid verbose prints in production
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post("https://api.openai.com/v1/audio/transcriptions", data=form, files=files, headers=headers)
            print(f"[STT DEBUG] Response status: {resp.status_code}")
            # Minimal error visibility; do not print full response bodies/headers
            if resp.status_code != 200:
                print(f"[STT DEBUG] OpenAI STT non-200: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            text = data.get("text", "")
            print(f"[STT DEBUG] Transcript length: {len(text)}")
            return text
    except Exception as e:
        print(f"[STT DEBUG] Error: {type(e).__name__}: {str(e)}")
        return ""



async def transcribe_with_azure(audio_bytes: bytes, content_type: str = "audio/webm") -> str:
    """Transcribe audio via Azure Speech SDK (short/batch) when configured.

    Supports common compressed containers (webm/opus, ogg/opus, mp3). Falls back to empty string on failure.
    """
    if not (settings.azure_speech_key and settings.azure_speech_region):
        return ""
    try:
        import azure.cognitiveservices.speech as speechsdk  # type: ignore
        try:
            from azure.cognitiveservices.speech.audio import (  # type: ignore
                AudioStreamFormat,
                AudioStreamContainerFormat,
                PushAudioInputStream,
            )
        except Exception:
            return ""

        ct = (content_type or "audio/webm").lower()
        # Pick compressed container supported by current SDK version; some versions
        # don't expose WEBM_OPUS. In that case, skip Azure and let caller fallback.
        container = None
        if "ogg" in ct:
            container = getattr(AudioStreamContainerFormat, "OGG_OPUS", None)
        elif "mp3" in ct or "mpeg" in ct:
            # MP3 support may not exist in all versions; fall back to OGG_OPUS if present
            container = getattr(AudioStreamContainerFormat, "MP3", None)
            if container is None:
                container = getattr(AudioStreamContainerFormat, "OGG_OPUS", None)
        elif "webm" in ct:
            container = getattr(AudioStreamContainerFormat, "WEBM_OPUS", None)

        if container is None:
            # Current Azure SDK lacks a matching compressed container → let caller fallback
            return ""

        stream_format = AudioStreamFormat(compressed_stream_format=container)
        push_stream = PushAudioInputStream(stream_format)

        # Write bytes to push stream in thread (SDK is sync/blocking)
        def _recognize() -> str:
            speech_config = speechsdk.SpeechConfig(subscription=settings.azure_speech_key, region=settings.azure_speech_region)
            speech_config.speech_recognition_language = "tr-TR"
            audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
            recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            # Feed bytes
            push_stream.write(audio_bytes)
            push_stream.close()
            result = recognizer.recognize_once()
            if result and getattr(result, "text", None):
                return result.text
            return ""

        text = await to_thread.run_sync(_recognize)
        return text or ""
    except Exception as e:
        print(f"[STT DEBUG] Azure batch error: {type(e).__name__}: {str(e)}")
        return ""


async def transcribe_audio_batch(audio_bytes: bytes, content_type: str = "audio/webm") -> tuple[str, str]:
    """Provider selection with fallback chain.

    Order:
    - If STT_PROVIDER=azure → Azure
    - If STT_PROVIDER=whisper or ENABLE_SERVERLESS_WHISPER=true → Whisper
    - auto (default): Azure → Whisper

    Returns (text, provider). Empty string means provider returned nothing.
    """
    prov = settings.stt_provider
    # Local queue worker path: enqueue job and blockingly wait for quick result if configured
    # This is a lightweight dev/local fallback; production should use a dedicated worker process.
    if settings.local_stt_queue:
        try:
            import redis.asyncio as aioredis  # type: ignore
            r = aioredis.from_url(settings.redis_url or "redis://localhost:6379", encoding="utf-8", decode_responses=True)
            job_key = f"stt:job:{base64.urlsafe_b64encode(os.urandom(8)).decode('ascii')}"
            # Store payload as hash to avoid huge messages in lists
            await r.hset(job_key, mapping={
                "content_type": content_type,
                "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
            })
            await r.rpush(settings.stt_queue_name, job_key)
            # Wait briefly for a result (best-effort)
            # Worker should write result to job_key:result
            for _ in range(30):  # ~3s
                res = await r.get(job_key + ":result")
                if res is not None:
                    await r.delete(job_key)
                    return (res or "").strip(), "local-queue"
                await asyncio.sleep(0.1)
        except Exception:
            pass
    if prov == "azure":
        text = await transcribe_with_azure(audio_bytes, content_type)
        return (text, "azure") if text else ("", "azure")
    if prov == "whisper" or settings.enable_serverless_whisper:
        text = await transcribe_with_whisper(audio_bytes, content_type)
        return (text, "whisper") if text else ("", "whisper")

    # auto: try Azure then Whisper
    text = await transcribe_with_azure(audio_bytes, content_type)
    if text:
        return text, "azure"
    text = await transcribe_with_whisper(audio_bytes, content_type)
    if text:
        return text, "whisper"
    return "", "auto"
