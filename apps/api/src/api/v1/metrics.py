from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.db.models.interview import Interview
from src.db.models.conversation import InterviewAnalysis

from datetime import datetime

router = APIRouter(tags=["metrics"])


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * pct
    f = int(k)
    c = min(f + 1, len(values_sorted) - 1)
    if f == c:
        return values_sorted[int(k)]
    d0 = values_sorted[f] * (c - k)
    d1 = values_sorted[c] * (k - f)
    return d0 + d1


@router.get("/api/v1/metrics")
async def get_metrics(session: AsyncSession = Depends(get_session)):
    """Return coarse system metrics for dashboard.

    - upload_p95_ms: P95 of (interview.completed_at - interview.created_at)
    - analysis_p95_ms: P95 of (analysis.created_at - interview.completed_at or interview.created_at)
    - error_rate: 1 - (#completed / #total interviews)
    """
    result = await session.execute(select(Interview))
    interviews = list(result.scalars().all())
    total = len(interviews)
    completed = [i for i in interviews if i.status == "completed" and i.completed_at]

    # Upload durations: created_at -> completed_at (fallback to 0 if missing)
    upload_durations_ms: list[float] = []
    for i in completed:
        try:
            dt_ms = (i.completed_at - i.created_at).total_seconds() * 1000.0  # type: ignore
            if dt_ms >= 0:
                upload_durations_ms.append(dt_ms)
        except Exception:
            pass

    # Analysis durations: completed_at (or created_at) -> analysis.created_at
    result2 = await session.execute(select(InterviewAnalysis))
    analyses = list(result2.scalars().all())
    analysis_map = {a.interview_id: a for a in analyses}
    analysis_durations_ms: list[float] = []
    for i in interviews:
        a = analysis_map.get(i.id)
        if not a:
            continue
        anchor = i.completed_at or i.created_at
        try:
            dt_ms = (a.created_at - anchor).total_seconds() * 1000.0  # type: ignore
            if dt_ms >= 0:
                analysis_durations_ms.append(dt_ms)
        except Exception:
            pass

    upload_p95 = _percentile(upload_durations_ms, 0.95)
    analysis_p95 = _percentile(analysis_durations_ms, 0.95)
    error_rate = None
    if total > 0:
        error_rate = 1.0 - (len(completed) / total)

    return {
        "upload_p95_ms": round(upload_p95) if upload_p95 is not None else None,
        "analysis_p95_ms": round(analysis_p95) if analysis_p95 is not None else None,
        "error_rate": error_rate,
    }


