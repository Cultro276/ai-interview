from __future__ import annotations

from dataclasses import dataclass, field
from typing import Deque, List, Dict, Tuple
from collections import deque
from threading import Lock
import json

try:
    from src.core.config import settings
except Exception:
    class _S:
        redis_url = None
    settings = _S()  # type: ignore


class _RedisMirror:
    def __init__(self, url: str | None) -> None:
        self._client: object | None = None
        if url:
            try:
                import redis  # type: ignore  # sync client to keep API unchanged
                self._client = redis.from_url(url, encoding="utf-8", decode_responses=True)  # type: ignore[attr-defined]
            except Exception:
                self._client = None

    def enabled(self) -> bool:
        return self._client is not None

    def record_turn(self, interview_id: int, role: str, text: str) -> None:
        if not self.enabled():
            return
        try:
            key = f"mem:{interview_id}:lastN"
            payload = json.dumps([role, (text or "").strip()])
            # Keep last 40
            client = self._client  # type: ignore[assignment]
            if client is None:
                return
            client.lpush(key, payload)  # type: ignore[attr-defined]
            client.ltrim(key, 0, 39)  # type: ignore[attr-defined]
            # Set a TTL to avoid stale buildup (e.g., 7 days)
            client.expire(key, 7 * 24 * 3600)  # type: ignore[attr-defined]
        except Exception:
            pass

    def update_summary(self, interview_id: int, summary: str) -> None:
        if not self.enabled():
            return
        try:
            client = self._client
            if client is None:
                return
            key = f"mem:{interview_id}:summary"
            client.set(key, (summary or "").strip()[:4000], ex=7 * 24 * 3600)  # type: ignore[attr-defined]
        except Exception:
            pass

    def upsert_fact(self, interview_id: int, k: str, v: str) -> None:
        if not self.enabled():
            return
        try:
            client = self._client
            if client is None:
                return
            key = f"mem:{interview_id}:facts"
            client.hset(key, str(k), (v or "").strip()[:1000])  # type: ignore[attr-defined]
            client.expire(key, 7 * 24 * 3600)  # type: ignore[attr-defined]
        except Exception:
            pass

    def snapshot(self, interview_id: int) -> dict | None:
        if not self.enabled():
            return None
        try:
            client = self._client
            if client is None:
                return None
            key_last = f"mem:{interview_id}:lastN"
            key_sum = f"mem:{interview_id}:summary"
            key_f = f"mem:{interview_id}:facts"
            last_raw = client.lrange(key_last, 0, 39) or []  # type: ignore[attr-defined]
            lastN = []
            for it in reversed(last_raw):  # reverse to chronological order
                try:
                    role, txt = json.loads(it)
                    lastN.append((role, txt))
                except Exception:
                    continue
            summary = client.get(key_sum) or ""  # type: ignore[attr-defined]
            facts = client.hgetall(key_f) or {}  # type: ignore[attr-defined]
            if (not lastN) and (not summary) and (not facts):
                return None
            return {
                "rolling_summary": summary,
                "facts": facts,
                "lastN": lastN,
            }
        except Exception:
            return None


@dataclass
class SessionMemory:
    interview_id: int
    last_turns: Deque[Tuple[str, str]] = field(default_factory=lambda: deque(maxlen=40))  # (role, text)
    rolling_summary: str = ""
    facts: Dict[str, str] = field(default_factory=dict)


class InMemoryStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._data: Dict[int, SessionMemory] = {}
        # Optional Redis mirror for cross-instance state
        self._mirror = _RedisMirror(getattr(settings, "redis_url", None))

    def get(self, interview_id: int) -> SessionMemory:
        with self._lock:
            mem = self._data.get(interview_id)
            if not mem:
                mem = SessionMemory(interview_id=interview_id)
                self._data[interview_id] = mem
            return mem

    def record_turn(self, interview_id: int, role: str, text: str) -> None:
        mem = self.get(interview_id)
        with self._lock:
            mem.last_turns.append((role, (text or "").strip()))
        try:
            self._mirror.record_turn(interview_id, role, text)
        except Exception:
            pass

    def update_summary(self, interview_id: int, summary: str) -> None:
        mem = self.get(interview_id)
        with self._lock:
            mem.rolling_summary = (summary or "").strip()[:4000]
        try:
            self._mirror.update_summary(interview_id, summary)
        except Exception:
            pass

    def upsert_fact(self, interview_id: int, key: str, value: str) -> None:
        mem = self.get(interview_id)
        with self._lock:
            mem.facts[str(key)] = (value or "").strip()[:1000]
        try:
            self._mirror.upsert_fact(interview_id, key, value)
        except Exception:
            pass

    def snapshot(self, interview_id: int) -> Dict:
        # Prefer Redis snapshot if available
        try:
            snap = self._mirror.snapshot(interview_id)
            if snap is not None:
                return snap
        except Exception:
            pass
        mem = self.get(interview_id)
        with self._lock:
            return {
                "rolling_summary": mem.rolling_summary,
                "facts": dict(mem.facts),
                "lastN": list(mem.last_turns),
            }


store = InMemoryStore()


