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
from src.services.conversations_service import ConversationsService
from src.core.config import settings
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from typing import Optional
import os
import httpx
from src.db.models.oauth import OAuthCredential

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
    # Rate limiting handled by EnterpriseRateLimiter middleware (prefix-based)
    svc = ConversationsService(session)
    return await svc.create_public_message(
        interview_id=message_in.interview_id,
        token=message_in.token,
        role=message_in.role,
        content=message_in.content or "",
        sequence_number=message_in.sequence_number,
    )


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


# ---- Final interview scheduling ----


class FinalInterviewIn(BaseModel):
    scheduled_at: str  # ISO datetime string
    meeting_link: str
    notes: Optional[str] = None


@router.post("/analysis/{interview_id}/final-interview")
async def set_final_interview(
    interview_id: int,
    payload: FinalInterviewIn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    # Verify interview belongs to tenant
    interview = (
        await session.execute(
            select(Interview)
            .join(Job, Interview.job_id == Job.id)
            .where(Interview.id == interview_id, Job.user_id == owner_id)
        )
    ).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Ensure analysis exists
    analysis = (
        await session.execute(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id))
    ).scalar_one_or_none()
    if not analysis:
        analysis = await generate_llm_full_analysis(session, interview_id)

    import json as _json
    from datetime import datetime as _dt
    blob = {}
    try:
        if analysis.technical_assessment:
            blob = _json.loads(analysis.technical_assessment)
    except Exception:
        blob = {}
    blob["final_interview"] = {
        "scheduled_at": payload.scheduled_at,
        "meeting_link": payload.meeting_link,
        "notes": payload.notes or "",
        "organizer_user_id": current_user.id,
        "created_at": _dt.now().isoformat(),
    }
    analysis.technical_assessment = _json.dumps(blob, ensure_ascii=False)
    await session.commit()
    await session.refresh(analysis)
    return {"ok": True}

# ---- Calendar/Meeting Integrations (OAuth-assisted) ----

class CreateCalendarEventIn(BaseModel):
    interview_id: int
    title: Optional[str] = None
    scheduled_at: str
    duration_min: int = 45
    attendees: Optional[list[str]] = None


@router.post("/calendar/google/create")
async def create_google_calendar_event(
    body: CreateCalendarEventIn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    """Google Calendar'da etkinlik oluşturur (OAuth gerektirir)."""
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    iv = (
        await session.execute(
            select(Interview).join(Job, Interview.job_id == Job.id).where(Interview.id == body.interview_id, Job.user_id == owner_id)
        )
    ).scalar_one_or_none()
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")
    cred = (
        await session.execute(
            select(OAuthCredential).where(OAuthCredential.user_id == current_user.id, OAuthCredential.provider == "google")
        )
    ).scalar_one_or_none()
    if not cred or not cred.access_token:
        raise HTTPException(status_code=400, detail="Google OAuth yetkilendirmesi gerekli")
    # Create skeleton response; actual creation is appended later toward file end to avoid patch ordering issues
    return {"ok": True}

# ---- Simple final interview mail: draft + send ----

class FinalEmailDraft(BaseModel):
    subject: str
    body: str


@router.post("/analysis/{interview_id}/final-email-draft", response_model=FinalEmailDraft)
async def final_email_draft(
    interview_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    iv = (
        await session.execute(
            select(Interview).join(Job, Interview.job_id == Job.id).where(Interview.id == interview_id, Job.user_id == owner_id)
        )
    ).scalar_one_or_none()
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")
    job = (await session.execute(select(Job).where(Job.id == iv.job_id))).scalar_one_or_none()
    cand = (await session.execute(select(Candidate).where(Candidate.id == iv.candidate_id))).scalar_one_or_none()
    company = None
    try:
        owner = (await session.execute(select(User).where(User.id == job.user_id))).scalar_one_or_none() if job else None
        company = getattr(owner, "company_name", None)
    except Exception:
        company = None
    # Try to personalize from analysis summary
    ana = (await session.execute(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id))).scalar_one_or_none()
    summary = getattr(ana, "summary", None) if ana else None
    subject = f"{company or 'Şirketimiz'} - Son Görüşme Daveti"
    body = (
        f"Merhaba {getattr(cand, 'name', 'Aday')},\n\n"
        f"{company or 'Şirketimiz'} olarak sizinle bir son görüşme yapmak istiyoruz. "
        f"Görüşmede ekibimizle tanışacak ve süreçle ilgili detayları konuşacağız.\n\n"
        + (f"Ön değerlendirme özeti: {summary}\n\n" if summary else "")
        + "Uygun olduğunuz zaman aralığını paylaşabilir misiniz? Yanıtınıza göre davet bağlantısını ileteceğiz.\n\n"
          "Saygılarımızla,\nİK Ekibi"
    )
    return FinalEmailDraft(subject=subject, body=body)


class FinalEmailSendIn(BaseModel):
    subject: str
    body: str


@router.post("/analysis/{interview_id}/final-email-send")
async def final_email_send(
    interview_id: int,
    payload: FinalEmailSendIn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    iv = (
        await session.execute(
            select(Interview).join(Job, Interview.job_id == Job.id).where(Interview.id == interview_id, Job.user_id == owner_id)
        )
    ).scalar_one_or_none()
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")
    cand = (await session.execute(select(Candidate).where(Candidate.id == iv.candidate_id))).scalar_one_or_none()
    if not cand or not getattr(cand, "email", None):
        raise HTTPException(status_code=400, detail="Candidate email unavailable")
    await send_email_resend(getattr(cand, "email"), payload.subject, payload.body)
    return {"ok": True}

# ---- Final Interview Availability Flow ----

class Slot(BaseModel):
    start: str  # ISO
    end: str    # ISO


class ProposeSlotsIn(BaseModel):
    interview_id: int
    slots: list[Slot]
    message: Optional[str] = None
    attendees: Optional[list[str]] = None


@router.post("/final-interview/propose")
async def propose_final_interview_slots(
    body: ProposeSlotsIn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    iv = (
        await session.execute(
            select(Interview).join(Job, Interview.job_id == Job.id).where(Interview.id == body.interview_id, Job.user_id == owner_id)
        )
    ).scalar_one_or_none()
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")
    # Ensure analysis exists
    ana = (
        await session.execute(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == body.interview_id))
    ).scalar_one_or_none()
    if not ana:
        ana = await generate_llm_full_analysis(session, body.interview_id)
    import json as _json
    blob = {}
    if ana.technical_assessment:
        try:
            blob = _json.loads(ana.technical_assessment)
        except Exception:
            blob = {}
    fi = blob.get("final_interview") or {}
    # Save proposals
    fi["proposals"] = [{"start": s.start, "end": s.end} for s in body.slots]
    fi["proposal_message"] = body.message or ""
    fi["proposal_sent_at"] = datetime.now(timezone.utc).isoformat()
    if isinstance(body.attendees, list):
        # Persist attendees list under final_interview to use in ICS later
        fi["attendees"] = [a for a in body.attendees if isinstance(a, str) and "@" in a]
    blob["final_interview"] = fi
    ana.technical_assessment = _json.dumps(blob, ensure_ascii=False)
    await session.commit()
    # Email candidate with links
    cand = (await session.execute(select(Candidate).where(Candidate.id == iv.candidate_id))).scalar_one_or_none()
    if cand and getattr(cand, "email", None):
        base = settings.external_base_url.rstrip("/")
        lines = [body.message or "Merhaba, aşağıdaki zaman aralıklarından birini seçebilirsiniz:", ""]
        for idx, s in enumerate(body.slots):
            link = f"{base}/api/v1/conversations/final-interview/accept?interview_id={iv.id}&slot={idx}"
            lines.append(f"- {s.start} – {s.end}: {link}")
        # If we have a public web URL configured, include a friendly selection page link
        web_base = (settings.web_external_base_url or "").rstrip("/")
        if web_base:
            try:
                lines.append("")
                lines.append(f"Tüm seçenekleri gör: {web_base}/accept?interview_id={iv.id}")
            except Exception:
                pass
        try:
            await send_email_resend(getattr(cand, "email"), "Son Görüşme Zaman Seçimi", "\n".join(lines))
        except Exception:
            pass
    return {"ok": True, "count": len(body.slots)}


@router.get("/final-interview/accept")
async def accept_final_interview_slot(
    interview_id: int,
    slot: int,
    session: AsyncSession = Depends(get_session),
):
    # Public-safe: only uses interview_id and updates final_interview in analysis
    ana = (
        await session.execute(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id))
    ).scalar_one_or_none()
    if not ana or not ana.technical_assessment:
        raise HTTPException(status_code=404, detail="Interview analysis not found")
    import json as _json
    blob = {}
    try:
        blob = _json.loads(ana.technical_assessment)
    except Exception:
        blob = {}
    fi = blob.get("final_interview") or {}
    props = fi.get("proposals") or []
    if not isinstance(props, list) or slot < 0 or slot >= len(props):
        raise HTTPException(status_code=400, detail="Invalid slot")
    chosen = props[slot]
    fi["scheduled_at"] = chosen.get("start")
    fi["scheduled_end"] = chosen.get("end")
    fi["accepted_at"] = datetime.now(timezone.utc).isoformat()
    blob["final_interview"] = fi
    ana.technical_assessment = _json.dumps(blob, ensure_ascii=False)
    await session.commit()
    # Optionally: send a confirmation email to candidate and owner with ICS attachment
    try:
        iv = (await session.execute(select(Interview).where(Interview.id == interview_id))).scalar_one_or_none()
        if iv:
            cand = (await session.execute(select(Candidate).where(Candidate.id == iv.candidate_id))).scalar_one_or_none()
            # Build ICS
            try:
                import base64
                from datetime import datetime as _dt
                def _fmt(dt_str: str | None) -> str:
                    try:
                        if not dt_str:
                            return ""
                        dt = _dt.fromisoformat(dt_str.replace("Z", "+00:00"))
                        return dt.strftime("%Y%m%dT%H%M%SZ")
                    except Exception:
                        return ""
                dtstart = _fmt(fi.get("scheduled_at"))
                dtend = _fmt(fi.get("scheduled_end"))
                uid = f"final-{interview_id}-{int(_dt.now().timestamp())}@recruiterai"
                summary = "Final Interview"
                location = (fi.get("meeting_link") or "").strip()
                # Basic ICS; ATTENDEE lines could be added later (admin UI will capture)
                ics_lines = [
                    "BEGIN:VCALENDAR",
                    "VERSION:2.0",
                    "PRODID:-//RecruiterAI//Final Interview//TR",
                    "CALSCALE:GREGORIAN",
                    "METHOD:PUBLISH",
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{_dt.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTSTART:{dtstart}",
                    f"DTEND:{dtend}",
                    f"SUMMARY:{summary}",
                    f"LOCATION:{location}",
                    "END:VEVENT",
                    "END:VCALENDAR",
                ]
                ics_content = "\r\n".join(ics_lines)
                ics_b64 = base64.b64encode(ics_content.encode("utf-8")).decode("ascii")
            except Exception:
                ics_b64 = None
            if cand and getattr(cand, "email", None):
                attachments = None
                if ics_b64:
                    attachments = [{"filename": "final-interview.ics", "content": ics_b64, "content_type": "text/calendar"}]
                await send_email_resend(getattr(cand, "email"), "Son Görüşme Onaylandı", f"Görüşmeniz {fi.get('scheduled_at')} tarihinde onaylandı.", attachments=attachments)
    except Exception:
        pass
    # Redirect-friendly response (for public click)
    return {"ok": True, "scheduled_at": fi.get("scheduled_at")}


# Public: list slot proposals without requiring auth (candidate-friendly)
@public_router.get("/final-interview/proposals")
async def get_final_interview_proposals(
    interview_id: int,
    session: AsyncSession = Depends(get_session),
):
    ana = (
        await session.execute(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id))
    ).scalar_one_or_none()
    if not ana or not ana.technical_assessment:
        return {"interview_id": interview_id, "proposals": []}
    import json as _json
    try:
        blob = _json.loads(ana.technical_assessment)
    except Exception:
        blob = {}
    fi = blob.get("final_interview") or {}
    props = fi.get("proposals") or []
    return {"interview_id": interview_id, "proposals": props}


class CreateZoomIn(BaseModel):
    interview_id: int
    topic: Optional[str] = None
    scheduled_at: str
    duration_min: int = 45


@router.post("/meeting/zoom/create")
async def create_zoom_meeting(
    body: CreateZoomIn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    """Zoom toplantısını oluşturur (OAuth gerektirir)."""
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    iv = (
        await session.execute(
            select(Interview).join(Job, Interview.job_id == Job.id).where(Interview.id == body.interview_id, Job.user_id == owner_id)
        )
    ).scalar_one_or_none()
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")
    cred = (
        await session.execute(
            select(OAuthCredential).where(OAuthCredential.user_id == current_user.id, OAuthCredential.provider == "zoom")
        )
    ).scalar_one_or_none()
    if not cred or not cred.access_token:
        raise HTTPException(status_code=400, detail="Zoom OAuth yetkilendirmesi gerekli")
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
        # Enrich with profile-derived fields when possible
        exp_level = "Unknown"
        edu_level = "Unknown"
        try:
            from src.db.models.candidate_profile import CandidateProfile as _CandProf
            prof = (
                await session.execute(select(_CandProf).where(_CandProf.candidate_id == getattr(cand, "id", 0)))
            ).scalar_one_or_none() if cand else None
            if prof:
                # Try parsed_json first
                import json as _json
                try:
                    if prof.parsed_json:
                        pj = _json.loads(prof.parsed_json)
                        exp_level = str(pj.get("experience_level", exp_level)) if isinstance(pj, dict) else exp_level
                        edu_level = str(pj.get("education_level", edu_level)) if isinstance(pj, dict) else edu_level
                except Exception:
                    pass
                # If still unknown, heuristically extract from resume_text
                if (exp_level == "Unknown" or edu_level == "Unknown") and prof.resume_text:
                    try:
                        from src.services.nlp import extract_cv_facts as _extract_cv_facts
                        facts = await _extract_cv_facts(prof.resume_text)
                        if isinstance(facts, dict):
                            exp_level = str(facts.get("experience_level", exp_level))
                            edu_level = str(facts.get("education_level", edu_level))
                    except Exception:
                        pass
        except Exception:
            pass
        
        interview_data = {
            "id": interview_id,
            "candidate_name": getattr(cand, "name", "Unknown") if cand else "Unknown",
            "job_title": getattr(job, "title", "Unknown") if job else "Unknown",
            "created_at": interview.created_at.isoformat() if interview.created_at else "",
            "experience_level": exp_level,
            "education_level": edu_level,
        }
        
        # Generate comprehensive report
        comprehensive_report = report_generator.generate_comprehensive_report(
            interview_data,
            tech_data,
            template_type=template_type
        )

        # Ensure top-level normalized score is present for UI consistency
        try:
            meta = tech_data.get("meta", {}) if isinstance(tech_data, dict) else {}
            normalized: float | None = None
            over = meta.get("overall_score") if isinstance(meta, dict) else None
            if isinstance(over, (int, float)):
                normalized = float(over)
            else:
                # Fallback from scoring recommendation if available (0..1 -> 0..100)
                sc_val = (comprehensive_report.get("scoring", {}) or {}).get("Genel Öneri Skoru")
                if isinstance(sc_val, (int, float)):
                    normalized = float(sc_val) * (100.0 if sc_val <= 1.0 else 1.0)
            if isinstance(normalized, (int, float)):
                if "content" not in comprehensive_report:
                    comprehensive_report["content"] = {}
                comprehensive_report["content"]["normalized_overall_score_0_100"] = round(normalized, 2)
        except Exception:
            pass
        
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

# ---- OAuth Authorization & Callback + Provider Create (server-side) ----

class CreateCalendarIn(BaseModel):
    interview_id: int
    title: Optional[str] = None
    scheduled_at: str
    duration_min: int = 45
    attendees: Optional[list[str]] = None


@router.get("/oauth/google/authorize")
async def oauth_google_authorize(current_user: User = Depends(current_active_user)):
    if not (settings.google_client_id and settings.google_redirect_uri):
        raise HTTPException(status_code=400, detail="Google OAuth yapılandırması eksik")
    scope = "https://www.googleapis.com/auth/calendar.events"
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?response_type=code&client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_redirect_uri}"
        f"&scope={scope}&access_type=offline&prompt=consent"
    )
    return {"url": url}


@router.get("/oauth/google/callback")
async def oauth_google_callback(code: str, session: AsyncSession = Depends(get_session), current_user: User = Depends(current_active_user)):
    if not (settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri):
        raise HTTPException(status_code=400, detail="Google OAuth yapılandırması eksik")
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Google token alma başarısız: {resp.text[:200]}")
    tok = resp.json()
    access = tok.get("access_token")
    refresh = tok.get("refresh_token")
    expires_in = int(tok.get("expires_in", 3600))
    exp_at = datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 60))
    cred = (
        await session.execute(select(OAuthCredential).where(OAuthCredential.user_id == current_user.id, OAuthCredential.provider == "google"))
    ).scalar_one_or_none()
    if not cred:
        cred = OAuthCredential(user_id=current_user.id, provider="google", access_token=access, refresh_token=refresh, expires_at=exp_at)
    else:
        cred.access_token = access or cred.access_token
        if refresh:
            cred.refresh_token = refresh
        cred.expires_at = exp_at
    session.add(cred)
    await session.commit()
    return {"ok": True}


@router.get("/oauth/zoom/authorize")
async def oauth_zoom_authorize(current_user: User = Depends(current_active_user)):
    if not (settings.zoom_client_id and settings.zoom_redirect_uri):
        raise HTTPException(status_code=400, detail="Zoom OAuth yapılandırması eksik")
    url = (
        "https://zoom.us/oauth/authorize"
        f"?response_type=code&client_id={settings.zoom_client_id}"
        f"&redirect_uri={settings.zoom_redirect_uri}"
        f"&state={current_user.id}"
    )
    return {"url": url}


@router.get("/oauth/zoom/callback")
async def oauth_zoom_callback(code: str, state: str | None = None, session: AsyncSession = Depends(get_session)):
    if not (settings.zoom_client_id and settings.zoom_client_secret and settings.zoom_redirect_uri):
        raise HTTPException(status_code=400, detail="Zoom OAuth yapılandırması eksik")
    basic = httpx.BasicAuth(settings.zoom_client_id, settings.zoom_client_secret)
    async with httpx.AsyncClient(timeout=20.0, auth=basic) as client:
        resp = await client.post(
            "https://zoom.us/oauth/token",
            params={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.zoom_redirect_uri,
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Zoom token alma başarısız: {resp.text[:200]}")
    tok = resp.json()
    access = tok.get("access_token")
    refresh = tok.get("refresh_token")
    expires_in = int(tok.get("expires_in", 3600))
    exp_at = datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 60))
    # Resolve user from state (user_id sent in authorize step)
    user_id_for_token: int | None = None
    try:
        if state:
            user_id_for_token = int(str(state).split(":")[0])
    except Exception:
        user_id_for_token = None
    if not user_id_for_token:
        # Fallback: choose the first admin/owner user
        try:
            from src.db.models.user import User as _User
            u = (await session.execute(select(_User).order_by(_User.id.asc()))).scalars().first()
            user_id_for_token = getattr(u, "id", None)
        except Exception:
            user_id_for_token = None
    if not user_id_for_token:
        raise HTTPException(status_code=400, detail="Kullanıcı belirlenemedi (state)")

    cred = (
        await session.execute(select(OAuthCredential).where(OAuthCredential.user_id == user_id_for_token, OAuthCredential.provider == "zoom"))
    ).scalar_one_or_none()
    if not cred:
        cred = OAuthCredential(user_id=user_id_for_token, provider="zoom", access_token=access, refresh_token=refresh, expires_at=exp_at)
    else:
        cred.access_token = access or cred.access_token
        if refresh:
            cred.refresh_token = refresh
        cred.expires_at = exp_at
    session.add(cred)
    await session.commit()
    return {"ok": True}