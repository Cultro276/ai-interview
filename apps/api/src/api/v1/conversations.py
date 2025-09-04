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
from fastapi import Request
from slowapi.util import get_remote_address
from slowapi import Limiter
from src.core.config import settings
from datetime import datetime, timezone, timedelta
from datetime import datetime, timezone

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
    return await generate_llm_full_analysis(session, interview_id)


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