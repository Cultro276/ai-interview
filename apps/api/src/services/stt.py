from __future__ import annotations

import io
from typing import Optional

import httpx

from src.core.config import settings
from anyio import to_thread


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
    """Use Azure batch STT only (as requested). No Whisper fallback.

    Returns (text, provider). Empty string means provider returned nothing.
    """
    text = await transcribe_with_azure(audio_bytes, content_type)
    if text:
        return text, "azure"
    return "", "azure"
