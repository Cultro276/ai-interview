from __future__ import annotations

import json
import time
from typing import Any, AsyncGenerator, Optional

from src.core.config import settings


_client = None


async def _get_client():
    global _client
    if _client is not None:
        return _client
    if not settings.redis_url:
        return None
    try:
        import redis.asyncio as aioredis  # type: ignore
        _client = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        return _client
    except Exception:
        return None


def _channel_for_interview(interview_id: int) -> str:
    return f"sse:interview:{interview_id}"


async def publish_event(channel: str, event: str, data: Any) -> None:
    client = await _get_client()
    if client is None:
        return
    payload = json.dumps({"event": event, "data": data, "ts": time.time()}, ensure_ascii=False)
    try:
        await client.publish(channel, payload)
    except Exception:
        # Best-effort; ignore fanout errors
        pass


async def subscribe_events(channel: str) -> AsyncGenerator[dict, None]:
    client = await _get_client()
    if client is None:
        # No Redis; yield nothing
        if False:
            yield {}
        return
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel)
        while True:
            try:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not msg:
                    continue
                if msg.get("type") == "message":
                    try:
                        obj = json.loads(msg.get("data") or "{}")
                        if isinstance(obj, dict):
                            yield obj
                    except Exception:
                        continue
            except Exception:
                # brief backoff
                await client.ping()
    finally:
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            pass


__all__ = [
    "publish_event",
    "subscribe_events",
    "_channel_for_interview",
]


