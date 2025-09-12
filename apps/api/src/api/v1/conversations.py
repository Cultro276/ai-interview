from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.auth import current_active_user, get_effective_owner_id, ensure_permission
from src.db.models.user import User
from src.db.models.conversation import ConversationMessage, InterviewAnalysis
from src.db.models.interview import Interview
from src.db.models.job import Job
from src.db.models.candidate import Candidate
from src.db.session import get_session
from src.api.v1.schemas import (
    ConversationMessageCreate, 
    ConversationMessageRead,
    InterviewAnalysisCreate,
    InterviewAnalysisRead
)
from src.services.analysis import generate_llm_full_analysis
from src.services.reporting import InterviewReportGenerator, export_to_markdown, export_to_structured_json
from src.core.metrics import collector, Timer
from src.core.mail import send_email_resend
from fastapi import Request
from slowapi.util import get_remote_address
from slowapi import Limiter
from src.core.config import settings
from datetime import datetime, timezone, timedelta
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/conversations", tags=["conversations"])

# Public router for candidate (token) submissions
public_router = APIRouter(prefix="/conversations", tags=["conversations-public"])  # included without auth in routes


# ---- Conversation Messages ----

@router.post("/messages", response_model=ConversationMessageRead, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_in: ConversationMessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Verify user owns the interview
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == message_in.interview_id, Job.user_id == owner_id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    message = ConversationMessage(**message_in.dict())
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


# Candidate-safe message creation that does not require admin JWT
class PublicConversationMessageCreate(ConversationMessageCreate):
    token: str


@public_router.post("/messages-public", response_model=ConversationMessageRead, status_code=status.HTTP_201_CREATED)
async def create_message_public(
    message_in: PublicConversationMessageCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    # Simple IP/token rate-limit: 10 requests per 10 seconds
    try:
        from fastapi import Request as _FReq
        req: _FReq = request  # type: ignore[assignment]
        limiter: Limiter = req.app.state.limiter  # type: ignore[attr-defined]
        await limiter.limit("10/10seconds")(lambda: None)(req)
    except Exception:
        pass
    # Verify candidate token is valid and belongs to the interview's candidate
    cand = (
        await session.execute(select(Candidate).where(Candidate.token == message_in.token))
    ).scalar_one_or_none()
    now_utc = datetime.now(timezone.utc)
    if not cand or cand.expires_at <= now_utc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    # Block public messages if any interview for candidate is already completed
    from src.db.models.interview import Interview
    from sqlalchemy import select as _select
    completed = (
        await session.execute(
            _select(Interview).where(Interview.candidate_id == cand.id, Interview.status == "completed")
        )
    ).first()
    if completed is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview already completed")

    interview = (
        await session.execute(select(Interview).where(Interview.id == message_in.interview_id))
    ).scalar_one_or_none()
    if not interview or interview.candidate_id != cand.id:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Deduplicate by (interview_id, sequence_number) to avoid StrictMode double posts
    existing = (
        await session.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.interview_id == message_in.interview_id,
                ConversationMessage.sequence_number == message_in.sequence_number,
            )
        )
    ).scalars().first()
    if existing:
        return existing

    # Prevent duplicate consecutive assistant questions in case of front-end replays
    try:
        from sqlalchemy import desc as _desc
        last = (
            await session.execute(
                select(ConversationMessage)
                .where(ConversationMessage.interview_id == message_in.interview_id)
                .order_by(ConversationMessage.sequence_number.desc())
            )
        ).scalars().first()
        # Compare enum value to incoming string to avoid false mismatches
        if last and getattr(last.role, "value", str(last.role)) == message_in.role and last.content.strip() == message_in.content.strip():
            return last
    except Exception:
        pass

    payload = {
        "interview_id": message_in.interview_id,
        "role": message_in.role,
        "content": (message_in.content or "").strip(),
        "sequence_number": message_in.sequence_number,
    }
    # Drop empty user messages (often STT artifacts like "..."), but keep assistant/system
    from src.db.models.conversation import MessageRole as _Role
    try:
        if payload["role"] == _Role.USER.value and len(payload["content"]) < 2:
            # Return a synthetic no-op response to keep client stable
            return ConversationMessage(
                id=0,
                interview_id=message_in.interview_id,
                role=_Role.USER,
                content="",
                timestamp=None,  # type: ignore[arg-type]
                sequence_number=message_in.sequence_number,
            )
    except Exception:
        pass
    message = ConversationMessage(**payload)
    session.add(message)
    try:
        await session.commit()
        await session.refresh(message)
        return message
    except IntegrityError:
        # Dedup both by (interview_id, sequence_number) and (interview_id, content, assistant-role)
        await session.rollback()
        existing_after = (
            await session.execute(
                select(ConversationMessage)
                .where(
                    ConversationMessage.interview_id == message_in.interview_id,
                    ConversationMessage.sequence_number == message_in.sequence_number,
                )
            )
        ).scalars().first()
        if existing_after:
            return existing_after
        # Assistant content unique check (partial index path)
        try:
            if payload["role"] == ConversationMessage.role.type.python_type.ASSISTANT:  # type: ignore[attr-defined]
                dup = (
                    await session.execute(
                        select(ConversationMessage)
                        .where(
                            ConversationMessage.interview_id == message_in.interview_id,
                            ConversationMessage.content == payload["content"],
                        )
                    )
                ).scalars().first()
                if dup:
                    return dup
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate message")


@router.get("/messages/{interview_id}", response_model=List[ConversationMessageRead])
async def get_conversation(
    interview_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Verify user owns the interview
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == owner_id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Get conversation messages
    result = await session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.interview_id == interview_id)
        .order_by(ConversationMessage.sequence_number)
    )
    return result.scalars().all()


# ---- External Scores: Work-sample / Panel Review / Outcome ----


class WorkSampleIn(BaseModel):
    name: str
    score_0_100: float
    weight_0_1: float | None = None
    notes: str | None = None


@router.post("/analysis/{interview_id}/work-sample")
async def add_work_sample(
    interview_id: int,
    payload: WorkSampleIn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Ownership
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == owner_id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Ensure analysis exists
    analysis = (
        await session.execute(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id))
    ).scalar_one_or_none()
    if not analysis:
        analysis = await generate_llm_full_analysis(session, interview_id)

    # Merge into technical_assessment JSON
    import json as _json
    blob = {}
    try:
        if analysis.technical_assessment:
            blob = _json.loads(analysis.technical_assessment)
    except Exception:
        blob = {}
    arr = blob.get("work_samples")
    if not isinstance(arr, list):
        arr = []
    arr.append({
        "name": payload.name,
        "score_0_100": float(payload.score_0_100),
        "weight_0_1": float(payload.weight_0_1) if payload.weight_0_1 is not None else None,
        "notes": payload.notes or "",
    })
    blob["work_samples"] = arr[-50:]
    analysis.technical_assessment = _json.dumps(blob, ensure_ascii=False)
    await session.commit()
    await session.refresh(analysis)
    return {"ok": True, "count": len(blob["work_samples"]) }


class PanelRubricItem(BaseModel):
    label: str
    score_0_100: float
    weight_0_1: float | None = None


class PanelReviewIn(BaseModel):
    decision: str  # Strong Hire|Hire|Hold|No Hire
    notes: str | None = None
    rubric: List[PanelRubricItem] | None = None


@router.post("/analysis/{interview_id}/panel")
async def set_panel_review(
    interview_id: int,
    payload: PanelReviewIn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == owner_id)
    )
    if not interview.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Interview not found")

    analysis = (
        await session.execute(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id))
    ).scalar_one_or_none()
    if not analysis:
        analysis = await generate_llm_full_analysis(session, interview_id)

    import json as _json
    blob = {}
    try:
        if analysis.technical_assessment:
            blob = _json.loads(analysis.technical_assessment)
    except Exception:
        blob = {}
    panel = {
        "decision": payload.decision,
        "notes": payload.notes or "",
        "rubric": [r.dict() for r in (payload.rubric or [])],
        "reviewed_at": datetime.now().isoformat(),
    }
    blob["panel_review"] = panel
    analysis.technical_assessment = _json.dumps(blob, ensure_ascii=False)
    await session.commit()
    await session.refresh(analysis)
    return {"ok": True}


# ---- Outcome tracking ----


class OutcomeIn(BaseModel):
    outcome: str  # hired|offer|no-offer
    outcome_date: Optional[str] = None  # ISO date string
    perf_30d: Optional[str] = None  # low|avg|high
    perf_90d: Optional[str] = None  # low|avg|high


@router.post("/analysis/{interview_id}/outcome")
async def set_outcome(
    interview_id: int,
    payload: OutcomeIn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == owner_id)
    )
    if not interview.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Interview not found")

    analysis = (
        await session.execute(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id))
    ).scalar_one_or_none()
    if not analysis:
        analysis = await generate_llm_full_analysis(session, interview_id)

    import json as _json
    blob = {}
    try:
        if analysis.technical_assessment:
            blob = _json.loads(analysis.technical_assessment)
    except Exception:
        blob = {}
    blob["outcome_tracking"] = {
        "outcome": payload.outcome,
        "outcome_date": payload.outcome_date,
        "perf_30d": payload.perf_30d,
        "perf_90d": payload.perf_90d,
    }
    analysis.technical_assessment = _json.dumps(blob, ensure_ascii=False)
    await session.commit()
    await session.refresh(analysis)
    return {"ok": True}


# ---- Calibration summary (AUC/ROC, histograms, FP/FN) ----


@router.get("/analysis/calibration/summary")
async def get_calibration_summary(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    """Return basic calibration metrics for overall scores vs outcomes.

    Outcome mapping: hired|offer -> 1 (positive), no-offer -> 0 (negative).
    Uses InterviewAnalysis.overall_score (0-100). Returns:
      { count, labeled_count, auc, roc: [{t, tpr, fpr}],
        hist: {pos:[int], neg:[int]}, fp: [{interview_id, score}], fn: [...] }
    """
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)

    # Fetch analyses under tenant
    rows = await session.execute(
        select(InterviewAnalysis, Interview)
        .join(Interview, InterviewAnalysis.interview_id == Interview.id)
        .join(Job, Interview.job_id == Job.id)
        .where(Job.user_id == owner_id)
    )
    pairs: list[tuple[int, float]] = []  # (label, score)
    ids: list[int] = []
    all_scores: list[float] = []
    import json as _json
    for ana, iv in rows.all():
        try:
            score = float(getattr(ana, "overall_score", None) or 0.0)
        except Exception:
            score = 0.0
        all_scores.append(score)
        label = None
        try:
            blob = _json.loads(ana.technical_assessment or "{}")
            out = blob.get("outcome_tracking") or {}
            oc = (out.get("outcome") or "").lower()
            if oc in {"hired", "offer"}:
                label = 1
            elif oc in {"no-offer", "no_offer", "no offer", "rejected"}:
                label = 0
        except Exception:
            label = None
        if label is not None:
            pairs.append((label, score))
            ids.append(iv.id)

    count = len(all_scores)
    labeled = len(pairs)
    if labeled < 2 or not any(l == 1 for l, _ in pairs) or not any(l == 0 for l, _ in pairs):
        return {
            "count": count,
            "labeled_count": labeled,
            "auc": None,
            "roc": [],
            "hist": {"pos": [], "neg": []},
            "fp": [],
            "fn": [],
        }

    # Build ROC
    # thresholds from 0..100 step 5
    thresholds = [float(t) for t in range(0, 101, 5)]
    roc = []
    pos_total = sum(1 for l, _ in pairs if l == 1)
    neg_total = sum(1 for l, _ in pairs if l == 0)
    for t in thresholds:
        tp = sum(1 for l, s in pairs if s >= t and l == 1)
        fp_ = sum(1 for l, s in pairs if s >= t and l == 0)
        fn = sum(1 for l, s in pairs if s < t and l == 1)
        tn = sum(1 for l, s in pairs if s < t and l == 0)
        tpr = (tp / pos_total) if pos_total else 0.0
        fpr = (fp_ / neg_total) if neg_total else 0.0
        roc.append({"t": t, "tpr": round(tpr, 4), "fpr": round(fpr, 4)})

    # AUC via trapezoidal rule over (fpr, tpr) sorted asc by fpr
    roc_sorted = sorted(roc, key=lambda x: x["fpr"])  # type: ignore[index]
    auc = 0.0
    for i in range(1, len(roc_sorted)):
        x0, y0 = roc_sorted[i - 1]["fpr"], roc_sorted[i - 1]["tpr"]
        x1, y1 = roc_sorted[i]["fpr"], roc_sorted[i]["tpr"]
        auc += (x1 - x0) * (y0 + y1) / 2.0
    auc = round(auc, 4)

    # Histograms (10 bins)
    def _hist(vals: list[float]) -> list[int]:
        bins = [0] * 10
        for v in vals:
            idx = int(min(9, max(0, v // 10)))
            bins[idx] += 1
        return bins
    pos_scores = [s for l, s in pairs if l == 1]
    neg_scores = [s for l, s in pairs if l == 0]
    hist = {"pos": _hist(pos_scores), "neg": _hist(neg_scores)}

    # FP/FN lists (top 10 by confidence)
    joined = list(zip(ids, [l for l, _ in pairs], [s for _, s in pairs]))
    fps = sorted([(iv_id, s) for iv_id, l, s in joined if l == 0], key=lambda x: -x[1])[:10]
    fns = sorted([(iv_id, s) for iv_id, l, s in joined if l == 1], key=lambda x: x[1])[:10]

    return {
        "count": count,
        "labeled_count": labeled,
        "auc": auc,
        "roc": roc_sorted,
        "hist": hist,
        "fp": [{"interview_id": i, "score": round(s, 2)} for i, s in fps],
        "fn": [{"interview_id": i, "score": round(s, 2)} for i, s in fns],
    }


# ---- Interview Analysis ----

@router.post("/analysis", response_model=InterviewAnalysisRead, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    analysis_in: InterviewAnalysisCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Verify user owns the interview
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == analysis_in.interview_id, Job.user_id == owner_id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Run LLM-based analysis to (re)generate content
    with Timer() as t:
        result = await generate_llm_full_analysis(session, analysis_in.interview_id)
    collector.record_analysis_ms(t.ms)
    # Notify responsible users via email (best-effort)
    try:
        # Find interview, job and owner email
        interview = (await session.execute(select(Interview).where(Interview.id == analysis_in.interview_id))).scalar_one_or_none()
        if interview:
            job = (await session.execute(select(Job).where(Job.id == interview.job_id))).scalar_one_or_none()
            if job:
                # Build recipient list: current_user + job owner + team members under same tenant (owner_user_id)
                recipients: set[str] = set()
                try:
                    # current_user (who likely initiated report view)
                    if getattr(current_user, "email", None):
                        recipients.add(current_user.email)
                except Exception:
                    pass
                # Prefer explicit creators when available
                try:
                    cand = (await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))).scalar_one_or_none()
                except Exception:
                    cand = None
                if cand and getattr(cand, "created_by_user_id", None):
                    creator = (await session.execute(select(User).where(User.id == cand.created_by_user_id))).scalar_one_or_none()
                    if creator and getattr(creator, "email", None):
                        recipients.add(creator.email)
                # job owner / creator
                owner = (await session.execute(select(User).where(User.id == job.user_id))).scalar_one_or_none()
                if owner and getattr(owner, "email", None):
                    recipients.add(owner.email)
                if getattr(job, "created_by_user_id", None):
                    jcreator = (await session.execute(select(User).where(User.id == job.created_by_user_id))).scalar_one_or_none()
                    if jcreator and getattr(jcreator, "email", None):
                        recipients.add(jcreator.email)
                # team members under same tenant
                team_rows = await session.execute(select(User).where(User.owner_user_id == job.user_id))
                team = team_rows.scalars().all()
                for u in team:
                    if getattr(u, "email", None) and (getattr(u, "role", None) in {"organization_admin", "hr_manager", "recruiter"} or not getattr(u, "role", None)):
                        recipients.add(u.email)

                if recipients:
                    cand = (await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))).scalar_one_or_none()
                    cand_name = getattr(cand, "name", None) or f"Aday #{interview.candidate_id}"
                    job_title = getattr(job, "title", None) or "Pozisyon"
                    subject = f"Rapor hazır: {cand_name} – {job_title}"
                    body = (
                        f"Merhaba,\n\n"
                        f"{cand_name} için {job_title} mülakat analiz raporu hazırlandı.\n"
                        f"Raporu panele giriş yaparak görüntüleyebilirsiniz.\n\n"
                        f"Görüşme ID: {interview.id}\n"
                        f"Saygılarımızla\n"
                        f"RecruiterAI"
                    )
                    for email in recipients:
                        try:
                            await send_email_resend(email, subject, body)
                        except Exception:
                            pass
    except Exception:
        pass
    return result


@router.get("/analysis/{interview_id}", response_model=InterviewAnalysisRead)
async def get_analysis(
    interview_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Verify user owns the interview
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == owner_id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Get or generate analysis (LLM)
    result = await session.execute(
        select(InterviewAnalysis)
        .where(InterviewAnalysis.interview_id == interview_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis:
        return analysis
    result = await generate_llm_full_analysis(session, interview_id)
    # Notify responsible users via email (best-effort)
    try:
        interview = (await session.execute(select(Interview).where(Interview.id == interview_id))).scalar_one_or_none()
        if interview:
            job = (await session.execute(select(Job).where(Job.id == interview.job_id))).scalar_one_or_none()
            if job:
                recipients: set[str] = set()
                try:
                    if getattr(current_user, "email", None):
                        recipients.add(current_user.email)
                except Exception:
                    pass
                # Prefer explicit creators when available
                try:
                    cand = (await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))).scalar_one_or_none()
                except Exception:
                    cand = None
                if cand and getattr(cand, "created_by_user_id", None):
                    creator = (await session.execute(select(User).where(User.id == cand.created_by_user_id))).scalar_one_or_none()
                    if creator and getattr(creator, "email", None):
                        recipients.add(creator.email)
                owner = (await session.execute(select(User).where(User.id == job.user_id))).scalar_one_or_none()
                if owner and getattr(owner, "email", None):
                    recipients.add(owner.email)
                if getattr(job, "created_by_user_id", None):
                    jcreator = (await session.execute(select(User).where(User.id == job.created_by_user_id))).scalar_one_or_none()
                    if jcreator and getattr(jcreator, "email", None):
                        recipients.add(jcreator.email)
                team_rows = await session.execute(select(User).where(User.owner_user_id == job.user_id))
                team = team_rows.scalars().all()
                for u in team:
                    if getattr(u, "email", None) and (getattr(u, "role", None) in {"organization_admin", "hr_manager", "recruiter"} or not getattr(u, "role", None)):
                        recipients.add(u.email)
                if recipients:
                    cand = (await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))).scalar_one_or_none()
                    cand_name = getattr(cand, "name", None) or f"Aday #{interview.candidate_id}"
                    job_title = getattr(job, "title", None) or "Pozisyon"
                    subject = f"Rapor hazır: {cand_name} – {job_title}"
                    body = (
                        f"Merhaba,\n\n"
                        f"{cand_name} için {job_title} mülakat analiz raporu hazırlandı.\n"
                        f"Raporu panele giriş yaparak görüntüleyebilirsiniz.\n\n"
                        f"Görüşme ID: {interview.id}\n"
                        f"Saygılarımızla\n"
                        f"RecruiterAI"
                    )
                    for email in recipients:
                        try:
                            await send_email_resend(email, subject, body)
                        except Exception:
                            pass
    except Exception:
        pass
    return result


# --- Requirements coverage (for dashboard heatmap) ---

@router.get("/analysis/{interview_id}/requirements-coverage")
async def get_requirements_coverage(
    interview_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    """Return compact coverage data for a given interview.

    Shape: { items: [{ label, must, weight, meets, evidence }], summary: str }
    """
    # Verify ownership
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == owner_id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    result = await session.execute(
        select(ConversationMessage, InterviewAnalysis)
        .join(InterviewAnalysis, InterviewAnalysis.interview_id == interview_id)
        .where(ConversationMessage.interview_id == interview_id)
    )
    row = await session.execute(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id))
    analysis = row.scalar_one_or_none()
    if not analysis or not getattr(analysis, "technical_assessment", None):
        # Trigger analysis generation if missing
        analysis = await generate_llm_full_analysis(session, interview_id)

    try:
        import json as _json
        blob = _json.loads(analysis.technical_assessment or "{}")
        spec = (blob.get("requirements_spec") or {}).get("items") or []
        matrix = (blob.get("job_fit") or {}).get("requirements_matrix") or []
        cover_map = {str(m.get("label","")): m for m in matrix if isinstance(m, dict)}
        out_items = []
        for it in spec:
            if not isinstance(it, dict):
                continue
            label = str(it.get("label",""))
            cov = cover_map.get(label, {})
            out_items.append({
                "label": label,
                "must": bool(it.get("must", False)),
                "weight": float(it.get("weight", 0.5) or 0.5),
                "meets": cov.get("meets", None),
                "evidence": cov.get("evidence", None),
            })
        return {"items": out_items, "summary": (blob.get("job_fit") or {}).get("job_fit_summary")}
    except Exception:
        return {"items": [], "summary": None}


@router.delete("/analysis/{interview_id}")
async def delete_analysis_if_expired(interview_id: int, session: AsyncSession = Depends(get_session), current_user: User = Depends(current_active_user)):
    # Verify ownership
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == owner_id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    # Enforce transcript retention: if older than retention, null out transcript_text
    try:
        if interview.created_at and interview.created_at < datetime.now(timezone.utc) - timedelta(days=settings.retention_transcript_days):
            interview.transcript_text = None
            await session.commit()
            return {"ok": True, "cleared": True}
    except Exception:
        pass
    return {"ok": True, "cleared": False}


@router.put("/analysis/{interview_id}", response_model=InterviewAnalysisRead)
async def update_analysis(
    interview_id: int,
    analysis_in: InterviewAnalysisCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Verify user owns the interview
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == owner_id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Recompute analysis from conversation messages (LLM)
    with Timer() as t:
        result = await generate_llm_full_analysis(session, interview_id)
    collector.record_analysis_ms(t.ms)
    return result


# ---- PHASE 1: COMPREHENSIVE REPORTING ENDPOINTS ----

@router.get("/reports/{interview_id}/comprehensive")
async def get_comprehensive_report(
    interview_id: int,
    template_type: str = "executive_summary",  # executive_summary, detailed_technical, behavioral_focus, hiring_decision
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    """Get comprehensive interview report with multiple template options"""
    # Verify ownership
    owner_id = get_effective_owner_id(current_user)
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == owner_id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Get existing analysis (comprehensive report should be in technical_assessment JSON)
    analysis = await session.execute(
        select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id)
    )
    analysis = analysis.scalar_one_or_none()
    
    if not analysis or not analysis.technical_assessment:
        # Generate analysis if missing
        analysis = await generate_llm_full_analysis(session, interview_id)
    
    # Parse technical_assessment JSON to get comprehensive_report
    import json
    try:
        tech_data = json.loads(analysis.technical_assessment) if analysis.technical_assessment else {}
        comprehensive_report = tech_data.get("comprehensive_report")
        
        if comprehensive_report and comprehensive_report.get("metadata", {}).get("template_type") == template_type:
            return comprehensive_report
        
        # Generate new report with requested template
        report_generator = InterviewReportGenerator()
        
        # Gather interview data
        job = await session.execute(select(Job).where(Job.id == interview.job_id))
        job = job.scalar_one_or_none()
        
        cand = await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))
        cand = cand.scalar_one_or_none()
        
        interview_data = {
            "id": interview_id,
            "candidate_name": getattr(cand, "name", "Unknown") if cand else "Unknown",
            "job_title": getattr(job, "title", "Unknown") if job else "Unknown",
            "created_at": interview.created_at.isoformat() if interview.created_at else ""
        }
        
        # Generate comprehensive report
        comprehensive_report = report_generator.generate_comprehensive_report(
            interview_data,
            tech_data,
            template_type=template_type
        )
        
        # Cache back into analysis.technical_assessment under "comprehensive_report"
        try:
            tech_data["comprehensive_report"] = comprehensive_report
            import json as _json
            analysis.technical_assessment = _json.dumps(tech_data, ensure_ascii=False)
            await session.commit()
        except Exception:
            pass
        return comprehensive_report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/reports/{interview_id}/export/{format}")
async def export_interview_report(
    interview_id: int,
    format: str,  # json, markdown, pdf, excel
    template_type: str = "executive_summary",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    """Export interview report in various formats"""
    # Get comprehensive report first
    report = await get_comprehensive_report(interview_id, template_type, session, current_user)
    
    if format == "json":
        content = export_to_structured_json(report)
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=interview_{interview_id}_report.json"}
        )
    
    elif format == "markdown":
        content = export_to_markdown(report)
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=interview_{interview_id}_report.md"}
        )
    
    elif format == "pdf":
        # For now, return structured data that frontend can convert to PDF
        return {
            "format": "pdf_data",
            "content": report,
            "download_url": f"/api/v1/conversations/reports/{interview_id}/export/json?template_type={template_type}",
            "message": "Use frontend PDF generation with this data"
        }
    
    elif format == "excel":
        # For now, return structured data that frontend can convert to Excel
        return {
            "format": "excel_data", 
            "content": report,
            "download_url": f"/api/v1/conversations/reports/{interview_id}/export/json?template_type={template_type}",
            "message": "Use frontend Excel generation with this data"
        }
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use: json, markdown, pdf, excel")


@router.get("/reports/bulk/{job_id}/candidates") 
async def get_bulk_candidate_reports(
    job_id: int,
    template_type: str = "executive_summary",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    """Get reports for all candidates in a job"""
    # Verify job ownership
    owner_id = get_effective_owner_id(current_user)
    job = await session.execute(
        select(Job).where(Job.id == job_id, Job.user_id == owner_id)
    )
    job = job.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get all interviews for this job
    interviews = await session.execute(
        select(Interview).where(Interview.job_id == job_id)
    )
    interviews = interviews.scalars().all()
    
    reports = []
    for interview in interviews:
        try:
            report = await get_comprehensive_report(interview.id, template_type, session, current_user)
            reports.append({
                "interview_id": interview.id,
                "candidate_id": interview.candidate_id,
                "report": report
            })
        except Exception as e:
            reports.append({
                "interview_id": interview.id,
                "candidate_id": interview.candidate_id,
                "error": str(e)
            })
    
    return {
        "job_id": job_id,
        "job_title": job.title,
        "template_type": template_type,
        "total_interviews": len(interviews),
        "successful_reports": len([r for r in reports if "error" not in r]),
        "reports": reports
    }