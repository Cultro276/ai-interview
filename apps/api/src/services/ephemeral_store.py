from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from src.core.config import settings


class EphemeralStore:
    """Ephemeral token storage backed by Redis when available.

    Falls back to in-memory dict if REDIS_URL is not configured.
    """

    def __init__(self) -> None:
        self._mem: dict[str, str] = {}
        self._redis = None
        if settings.redis_url:
            try:
                import redis.asyncio as aioredis  # type: ignore
                self._redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
            except Exception:
                self._redis = None

    async def put(self, key: str, data: dict[str, Any], ttl_seconds: int = 90) -> None:
        payload = json.dumps(data, ensure_ascii=False)
        if self._redis is not None:
            try:
                await self._redis.set(key, payload, ex=ttl_seconds)
                return
            except Exception:
                pass
        # Fallback to memory (no TTL enforcement; best-effort)
        self._mem[key] = payload

    async def get(self, key: str) -> Optional[dict[str, Any]]:
        if self._redis is not None:
            try:
                val = await self._redis.get(key)
                if not val:
                    return None
                return json.loads(val)
            except Exception:
                pass
        raw = self._mem.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def delete(self, key: str) -> None:
        if self._redis is not None:
            try:
                await self._redis.delete(key)
                return
            except Exception:
                pass
        self._mem.pop(key, None)

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex


store = EphemeralStore()


