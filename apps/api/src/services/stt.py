from __future__ import annotations

import io
from typing import Optional

import httpx

from src.core.config import settings


async def transcribe_with_whisper(audio_bytes: bytes, content_type: str = "audio/webm") -> str:
    """Send audio to OpenAI Whisper API if OPENAI_API_KEY is configured.

    Falls back to empty string on failure so the caller can decide next steps.
    """
    if not settings.openai_api_key:
        return ""
    try:
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
        }
        form = {
            "model": (None, "whisper-1"),
        }
        files = {
            "file": ("audio.webm", io.BytesIO(audio_bytes), content_type),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post("https://api.openai.com/v1/audio/transcriptions", data=form, files=files, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("text", "")
    except Exception:
        return ""


