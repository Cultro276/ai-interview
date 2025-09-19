from __future__ import annotations

import asyncio
import base64
import os
from typing import Optional

import redis.asyncio as aioredis  # type: ignore

from src.core.config import settings
from src.services.stt import transcribe_with_azure, transcribe_with_whisper


async def _process_one(r: aioredis.Redis) -> None:
    key = await r.lpop(settings.stt_queue_name)
    if not key:
        await asyncio.sleep(0.2)
        return
    try:
        payload = await r.hgetall(key)
        if not payload:
            return
        ct = payload.get("content_type") or "audio/webm"
        b64 = payload.get("audio_b64") or ""
        audio = base64.b64decode(b64)
        # Try Azure first if configured
        text = ""
        if settings.stt_provider in {"azure", "auto"}:
            text = await transcribe_with_azure(audio, ct)
        if not text:
            text = await transcribe_with_whisper(audio, ct)
        await r.set(key + ":result", text or "")
    except Exception:
        try:
            await r.set(key + ":result", "")
        except Exception:
            pass
    finally:
        # Let stt.py delete the job key after reading result to avoid race
        pass


async def run_worker_forever() -> None:
    url = settings.redis_url or "redis://localhost:6379"
    r = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
    try:
        while True:
            await _process_one(r)
    finally:
        try:
            await r.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run_worker_forever())


