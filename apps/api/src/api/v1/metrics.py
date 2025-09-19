from fastapi import APIRouter, Depends

from src.core.metrics import collector
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import Depends
from datetime import datetime, timedelta, timezone
from src.db.session import get_session
from src.auth import current_active_user, get_effective_owner_id
from src.db.models.user import User
from src.db.models.interview import Interview
from src.db.models.candidate import Candidate
from src.db.models.job import Job
from src.core.s3 import upsert_lifecycle_rule
from src.core.config import settings
import json as _json


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics():
    return collector.snapshot()


@router.get("/weekly")
async def weekly_summary(session: AsyncSession = Depends(get_session), current_user: User = Depends(current_active_user)):
    """Minimal weekly ops summary. Placeholder for fairness metrics.

    Returns counts of created and completed interviews over last 7 days.
    """
    # created_at is stored as naive (timestamp without time zone), completed_at is tz-aware
    now_aware = datetime.now(timezone.utc)
    week_ago_aware = now_aware - timedelta(days=7)
    week_ago_naive = week_ago_aware.replace(tzinfo=None)

    owner_id = get_effective_owner_id(current_user)
    q_total = await session.execute(
        select(func.count())
        .select_from(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.created_at >= week_ago_naive, Job.user_id == owner_id)
    )
    q_completed = await session.execute(
        select(func.count())
        .select_from(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.completed_at >= week_ago_aware, Job.user_id == owner_id)
    )
    return {
        "interviews_created_7d": int(q_total.scalar() or 0),
        "interviews_completed_7d": int(q_completed.scalar() or 0),
    }


@router.get("/adverse/{job_id}")
async def adverse_impact_proxy(job_id: int, session: AsyncSession = Depends(get_session)):
    """Proxy metrics for adverse impact without sensitive attributes.

    Uses process metrics only (completion rates by simple cohorts).
    """
    total = await session.execute(select(func.count()).select_from(Interview).where(Interview.job_id == job_id))
    completed = await session.execute(select(func.count()).select_from(Interview).where(Interview.job_id == job_id, Interview.status == "completed"))
    return {
        "job_id": job_id,
        "completion_rate": (int(completed.scalar() or 0) / max(1, int(total.scalar() or 0)))
    }


@router.get("/time-to-hire/{job_id}")
async def time_to_hire(job_id: int, session: AsyncSession = Depends(get_session)):
    """Rough time-to-hire proxy: average interview duration (created->completed)."""
    rows = await session.execute(select(Interview.created_at, Interview.completed_at).where(Interview.job_id == job_id, Interview.completed_at.is_not(None)))
    import datetime as _dt
    diffs = []
    for created_at, completed_at in rows.all():
        try:
            diffs.append((completed_at - created_at).total_seconds())
        except Exception:
            pass
    avg_s = (sum(diffs) / len(diffs)) if diffs else 0.0
    return {"job_id": job_id, "avg_completed_seconds": round(avg_s, 2)}


@router.get("/rubric/{job_id}")
async def rubric_breakdown(job_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(current_active_user)):
    """Return rubric weights for a job from rubric_json or inferred defaults."""
    owner_id = get_effective_owner_id(current_user)
    job = (
        await session.execute(select(Job).where(Job.id == job_id, Job.user_id == owner_id))
    ).scalar_one_or_none()
    if not job:
        return {"job_id": job_id, "criteria": []}
    try:
        if job.rubric_json:
            cfg = _json.loads(job.rubric_json)
            arr = cfg.get("criteria") if isinstance(cfg, dict) else []
            if isinstance(arr, list):
                return {"job_id": job_id, "criteria": arr}
    except Exception:
        pass
    # fallback to inferred defaults
    from src.services.comprehensive_analyzer import ComprehensiveAnalyzer
    weights = ComprehensiveAnalyzer()._infer_rubric_weights(job.title or "")
    return {"job_id": job_id, "criteria": [
        {"label": "Problem Çözme", "weight": weights.get("problem", 0.25)},
        {"label": "Teknik Yeterlilik", "weight": weights.get("technical", 0.35)},
        {"label": "İletişim", "weight": weights.get("communication", 0.2)},
        {"label": "Kültür/İş Uygunluğu", "weight": weights.get("culture", 0.2)},
    ]}


@router.post("/lifecycle/media")
async def set_media_lifecycle():
    """Set S3 lifecycle for media/ prefix using configured retention days."""
    try:
        cfg = upsert_lifecycle_rule(prefix="media/", expire_days=settings.retention_media_days)
        return cfg
    except Exception as e:
        return {"error": str(e)}


