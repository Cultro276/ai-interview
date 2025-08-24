from __future__ import annotations

import io
from typing import Optional

import httpx

from src.core.config import settings


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


