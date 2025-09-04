from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import perf_counter
from typing import Deque, Dict, Optional


@dataclass
class _Series:
    values: Deque[float]
    lock: Lock


class MetricsCollector:
    """In-memory, best-effort metrics collector for dev/staging.

    Tracks simple latency series for upload and analysis, plus error counts.
    """

    def __init__(self, capacity: int = 500) -> None:
        self.capacity = capacity
        self.upload_ms = _Series(deque(maxlen=capacity), Lock())
        self.analysis_ms = _Series(deque(maxlen=capacity), Lock())
        self.error_count: int = 0
        self._error_lock = Lock()
        # Track presign issuance times by token to estimate upload duration
        self._presign_issued_at: Dict[str, float] = {}
        self._presign_lock = Lock()
        # Generic counters and histograms for ad-hoc metrics
        self.counters: Dict[str, int] = {}
        self._counter_lock = Lock()
        self.histograms: Dict[str, _Series] = {}
        self._hists_lock = Lock()

    def mark_presign_issued(self, token: str) -> None:
        now = perf_counter()
        with self._presign_lock:
            self._presign_issued_at[token] = now

    def record_upload_completion(self, token: str) -> Optional[float]:
        """Estimate upload duration from presign issuance to completion mark.

        Returns the measured ms if available.
        """
        end = perf_counter()
        start: Optional[float] = None
        with self._presign_lock:
            start = self._presign_issued_at.pop(token, None)
        if start is None:
            return None
        ms = max(0.0, (end - start) * 1000.0)
        with self.upload_ms.lock:
            self.upload_ms.values.append(ms)
        return ms

    def record_analysis_ms(self, ms: float) -> None:
        with self.analysis_ms.lock:
            self.analysis_ms.values.append(max(0.0, ms))

    def record_error(self) -> None:
        with self._error_lock:
            self.error_count += 1

    # --- Generic helpers used by various call sites ---
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a named counter by value (default 1)."""
        with self._counter_lock:
            self.counters[name] = self.counters.get(name, 0) + int(value)

    def record_histogram(self, name: str, value: float) -> None:
        """Append a value to a named histogram series (P95 can be computed externally)."""
        with self._hists_lock:
            series = self.histograms.get(name)
            if series is None:
                series = _Series(deque(maxlen=self.capacity), Lock())
                self.histograms[name] = series
        with series.lock:  # type: ignore[has-type]
            series.values.append(float(value))

    def _percentile(self, series: _Series, p: float) -> float:
        with series.lock:
            values = list(series.values)
        if not values:
            return 0.0
        values.sort()
        k = int(round((p / 100.0) * (len(values) - 1)))
        return float(values[k])

    def snapshot(self) -> dict:
        # Approximate error rate as errors / (N_upload + N_analysis + 1)
        with self.upload_ms.lock:
            n_upload = len(self.upload_ms.values)
        with self.analysis_ms.lock:
            n_analysis = len(self.analysis_ms.values)
        denom = max(1, n_upload + n_analysis)
        with self._error_lock:
            errors = self.error_count
        return {
            "upload_p95_ms": round(self._percentile(self.upload_ms, 95), 2),
            "analysis_p95_ms": round(self._percentile(self.analysis_ms, 95), 2),
            "error_rate": round(errors / denom, 4),
            "counts": {
                "uploads": n_upload,
                "analyses": n_analysis,
                "errors": errors,
            },
        }


# Singleton instance
collector = MetricsCollector()


class Timer:
    """Context manager to time an operation and feed metrics."""

    def __init__(self) -> None:
        self._start = 0.0
        self.ms = 0.0

    def __enter__(self) -> "Timer":
        self._start = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001, D401
        end = perf_counter()
        self.ms = max(0.0, (end - self._start) * 1000.0)
        # Do not record automatically; caller decides which series to update.
        return None


