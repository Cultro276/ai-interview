from __future__ import annotations

from typing import List, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.interview import Interview
from src.db.models.job import Job

from src.db.models.conversation import ConversationMessage, InterviewAnalysis
from src.db.models.interview import Interview


async def generate_rule_based_analysis(session: AsyncSession, interview_id: int) -> InterviewAnalysis:
    """
    Generate a lightweight, rule-based analysis from conversation messages.
    This avoids external AI dependencies and provides immediate value.
    """
    result = await session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.interview_id == interview_id)
        .order_by(ConversationMessage.sequence_number)
    )
    messages: List[ConversationMessage] = list(result.scalars().all())

    # Pull job description for context
    job_desc = ""
    job = (
        await session.execute(
            select(Job)
            .join(Interview, Interview.job_id == Job.id)
            .where(Interview.id == interview_id)
        )
    ).scalar_one_or_none()
    if job and job.description:
        job_desc = job.description

    # Initialize variables to avoid unbound warnings in later usage
    filler_count = 0
    avg_ans_latency = None
    avg_q_gap = None

    if not messages:
        summary = "No conversation captured."
        strengths = "N/A"
        weaknesses = "N/A"
        overall = 0.0
        comm = 0.0
        tech = 0.0
        culture = 0.0
    else:
        assistant_msgs = [m for m in messages if m.role.value == "assistant"]
        user_msgs = [m for m in messages if m.role.value == "user"]

        # Simple heuristics
        total_user_words = sum(len(m.content.split()) for m in user_msgs)
        avg_user_len = total_user_words / max(1, len(user_msgs))
        filler_words = ["şey", "hani", "yani", "ıı", "ee"]
        filler_count = sum(sum(1 for w in filler_words if w in m.content.lower()) for m in user_msgs)

        # Scores (0-100)
        communication_score = max(0.0, min(100.0, 60.0 + (avg_user_len * 2) - (filler_count * 5)))
        _tech_kws = ["api", "database", "microservice", "docker", "aws"]
        _culture_kws = ["takım", "iletişim", "liderlik", "uyum"]
        technical_score = 50.0 + min(30.0, len([m for m in user_msgs if any(k in m.content.lower() for k in _tech_kws)]) * 10.0)
        cultural_fit_score = 50.0 + min(30.0, len([m for m in user_msgs if any(k in m.content.lower() for k in _culture_kws)]) * 10.0)
        # Simple unweighted overall (average of available dimensions)
        overall = round((communication_score + technical_score + cultural_fit_score) / 3.0, 2)

        # Summary
        first_q = assistant_msgs[0].content if assistant_msgs else ""
        last_a = user_msgs[-1].content if user_msgs else ""
        summary = (
            f"Interview contained {len(assistant_msgs)} questions and {len(user_msgs)} answers. "
            f"Average answer length was {avg_user_len:.1f} words. "
            f"Sample Q: '{first_q[:120]}...' Sample A: '{last_a[:120]}...'"
        )
        if job_desc:
            summary += f" Job context: '{job_desc[:160]}...'"

        strengths_list: List[str] = []
        weaknesses_list: List[str] = []
        if communication_score >= 70:
            strengths_list.append("Clear and sufficiently detailed answers")
        else:
            weaknesses_list.append("Answers could be more detailed and concise")
        if technical_score >= 70:
            strengths_list.append("Demonstrates technical awareness (keywords present)")
        else:
            weaknesses_list.append("Limited explicit technical detail detected in responses")
        if filler_count > 3:
            weaknesses_list.append("Frequent filler words detected")
        else:
            strengths_list.append("Minimal filler words")

        strengths = " • ".join(strengths_list) or "—"
        weaknesses = " • ".join(weaknesses_list) or "—"

        comm = round(communication_score, 2)
        tech = round(technical_score, 2)
        culture = round(cultural_fit_score, 2)

        # Timing metrics (average seconds)
        try:
            from datetime import timedelta
            ans_latencies: List[float] = []
            for idx, m in enumerate(messages):
                if m.role.value != "assistant":
                    continue
                # Find next user message after this assistant message
                for j in range(idx + 1, len(messages)):
                    mj = messages[j]
                    if mj.role.value == "user":
                        delta = (mj.timestamp - m.timestamp).total_seconds() if mj.timestamp and m.timestamp else None
                        if isinstance(delta, (int, float)) and 0 <= delta <= 3600 * 3:
                            ans_latencies.append(float(delta))
                        break
            q_times = [m.timestamp for m in messages if m.role.value == "assistant" and m.timestamp]
            q_gaps: List[float] = []
            for a, b in zip(q_times, q_times[1:]):
                try:
                    d = (b - a).total_seconds()
                    if isinstance(d, (int, float)) and 0 <= d <= 3600 * 6:
                        q_gaps.append(float(d))
                except Exception:
                    pass
            avg_ans_latency = round(sum(ans_latencies) / len(ans_latencies), 1) if ans_latencies else None
            avg_q_gap = round(sum(q_gaps) / len(q_gaps), 1) if q_gaps else None
        except Exception:
            avg_ans_latency = None
            avg_q_gap = None

        # Removed requirements coverage

    # Upsert analysis
    existing = (
        await session.execute(
            select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id)
        )
    ).scalar_one_or_none()

    # Prepare competency JSON for technical_assessment
    # Build meta stats for UI
    meta = {
        "question_count": len([m for m in messages if m.role.value == "assistant"]),
        "answer_count": len([m for m in messages if m.role.value == "user"]),
        "avg_answer_length_words": round(
            (
                sum(len(m.content.split()) for m in messages if m.role.value == "user")
                / max(1, len([m for m in messages if m.role.value == "user"]))
            ),
            1,
        ),
        "filler_word_count": filler_count,
        "top_keywords": sorted(
            list(
                {
                    k
                    for m in (messages or [])
                    if m.role.value == "user"
                    for k in (
                        [
                            "api",
                            "database",
                            "microservice",
                            "docker",
                            "aws",
                            "takım",
                            "iletişim",
                            "liderlik",
                            "uyum",
                        ]
                    )
                    if k in m.content.lower()
                }
            )
        ),
        "avg_answer_latency_seconds": avg_ans_latency,
        "avg_inter_question_gap_seconds": avg_q_gap,
    }
    competency_json = {"competencies": {"communication": comm, "technical": tech, "cultural_fit": culture}, "meta": meta}

    if existing:
        existing.overall_score = overall
        existing.summary = summary
        existing.strengths = strengths
        existing.weaknesses = weaknesses
        existing.communication_score = comm
        existing.technical_score = tech
        existing.cultural_fit_score = culture
        try:
            import json
            existing.technical_assessment = json.dumps(competency_json, ensure_ascii=False)
        except Exception:
            pass
        await session.commit()
        await session.refresh(existing)
        return existing
    else:
        analysis = InterviewAnalysis(
            interview_id=interview_id,
            overall_score=overall,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            communication_score=comm,
            technical_score=tech,
            cultural_fit_score=culture,
            model_used="rule-based-v1",
        )
        try:
            import json
            analysis.technical_assessment = json.dumps(competency_json, ensure_ascii=False)
        except Exception:
            pass
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)
        return analysis


async def merge_enrichment_into_analysis(
    session: AsyncSession,
    interview_id: int,
    enrichment: dict,
) -> InterviewAnalysis:
    """Merge enrichment payload (soft_skills/speech/vision/llm_summary) into technical_assessment JSON.

    Creates analysis if missing by calling rule-based generator first.
    """
    analysis = (
        await session.execute(
            select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id)
        )
    ).scalar_one_or_none()
    if not analysis:
        analysis = await generate_rule_based_analysis(session, interview_id)

    import json
    blob = {}
    try:
        if analysis.technical_assessment:
            blob = json.loads(analysis.technical_assessment)
    except Exception:
        blob = {}
    # Merge keys conservatively; accept broader set used across the pipeline
    mergeable_scalar_keys = (
        "soft_skills",
        "speech",
        "vision",
        "llm_summary",
        "dialog_plan",
        "hr_criteria",
        "job_fit",
        "ai_opinion",
    )
    for k in mergeable_scalar_keys:
        if k in enrichment and enrichment[k]:
            blob[k] = enrichment[k]

    # Turn-level evidence: append to a list for chronological inspection
    if "turn_evidence" in enrichment and enrichment["turn_evidence"]:
        try:
            existing_list = blob.get("turn_evidence")
            if not isinstance(existing_list, list):
                existing_list = []
            # Normalize single item vs list
            incoming = enrichment["turn_evidence"]
            if isinstance(incoming, list):
                existing_list.extend([it for it in incoming if it])
            else:
                existing_list.append(incoming)
            blob["turn_evidence"] = existing_list[-200:]  # cap to last N to avoid unbounded growth
        except Exception:
            # If anything goes wrong, skip silently to avoid blocking analysis merge
            pass
    analysis.technical_assessment = json.dumps(blob, ensure_ascii=False)
    await session.commit()
    await session.refresh(analysis)
    return analysis


# --- LLM-based full analysis (job + resume + transcript) ---

async def generate_comprehensive_interview_analysis(session: AsyncSession, interview_id: int) -> InterviewAnalysis:
    """
    Generate comprehensive interview analysis using unified analyzers.
    Replaces both generate_llm_full_analysis and enrich_with_job_and_hr with efficient implementation.
    """
    from src.services.interview_engine import InterviewEngine
    from src.services.comprehensive_analyzer import comprehensive_interview_analysis

    # Load interview context using InterviewEngine
    engine = InterviewEngine(session)
    context = await engine.load_context(interview_id)

    # Ensure we have minimum required data
    if not context.transcript_text.strip():
        # Try to build from conversation messages if transcript is empty
        from sqlalchemy import select as _select
        msgs = (
            await session.execute(
                _select(ConversationMessage)
                .where(ConversationMessage.interview_id == interview_id)
                .order_by(ConversationMessage.sequence_number)
            )
        ).scalars().all()
        if msgs:
            def _prefix(m):
                return ("Interviewer" if m.role.value == "assistant" 
                       else "Candidate" if m.role.value == "user" 
                       else "System")
            context.transcript_text = "\n\n".join([
                f"{_prefix(m)}: {m.content.strip()}" 
                for m in msgs 
                if (m.content or "").strip()
            ])

    # Fallback: use resume as proxy transcript if still no transcript
    if not context.transcript_text.strip() and context.resume_text.strip():
        context.transcript_text = context.resume_text[:5000]

    if not context.transcript_text.strip():
        raise ValueError("No transcript or resume available for analysis")

    # Trim overly long transcripts for performance
    if len(context.transcript_text) > 50000:
        context.transcript_text = context.transcript_text[:50000]

    # Run comprehensive analysis using new unified analyzer
    analysis_results = await comprehensive_interview_analysis(
        job_desc=context.job_description,
        transcript_text=context.transcript_text,
        resume_text=context.resume_text,
        candidate_name=context.candidate_name,
        job_title=context.job_title
    )

    # Extract overall score from results
    overall_score = analysis_results.get("meta", {}).get("overall_score")

    # Extract summary from hiring decision
    summary = ""
    hiring_decision = analysis_results.get("hiring_decision", {})
    if isinstance(hiring_decision, dict):
        summary = str(hiring_decision.get("overall_assessment", ""))[:2000]

    # Also try job_fit summary as fallback
    if not summary:
        job_fit = analysis_results.get("job_fit", {})
        if isinstance(job_fit, dict):
            summary = str(job_fit.get("job_fit_summary", ""))[:2000]

    # Upsert analysis record
    existing = (
        await session.execute(
            select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id)
        )
    ).scalar_one_or_none()
    
    import json
    
    if existing:
        existing.overall_score = overall_score
        existing.summary = summary or existing.summary
        existing.model_used = "comprehensive-v1"
        
        # Merge with existing technical assessment
        try:
            base = {}
            if existing.technical_assessment:
                try:
                    base = json.loads(existing.technical_assessment)
                except Exception:
                    base = {}
            base.update(analysis_results)
            existing.technical_assessment = json.dumps(base, ensure_ascii=False)
        except Exception:
            existing.technical_assessment = json.dumps(analysis_results, ensure_ascii=False)
    else:
        analysis = InterviewAnalysis(
            interview_id=interview_id,
            overall_score=overall_score,
            summary=summary,
            strengths=None,
            weaknesses=None,
            communication_score=None,
            technical_score=None,
            cultural_fit_score=None,
            model_used="comprehensive-v1",
        )
        try:
            analysis.technical_assessment = json.dumps(analysis_results, ensure_ascii=False)
        except Exception:
            pass
        session.add(analysis)
        existing = analysis

    await session.commit()
    await session.refresh(existing)
    
    return existing


async def generate_llm_full_analysis(session: AsyncSession, interview_id: int) -> InterviewAnalysis:
    """
    DEPRECATED: Use generate_comprehensive_interview_analysis instead.
    Maintained for backward compatibility with existing API endpoints.
    """
    return await generate_comprehensive_interview_analysis(session, interview_id)


async def enrich_with_job_and_hr(
    session: AsyncSession,
    interview_id: int,
) -> None:
    """
    DEPRECATED: Use generate_comprehensive_interview_analysis instead.
    Maintained for backward compatibility only.
    """
    try:
        await generate_comprehensive_interview_analysis(session, interview_id)
    except Exception:
        # Fallback to ensure no complete failure
        pass


# --- Pre-interview dialog planning (CV + Job) ---

async def precompute_dialog_plan(session: AsyncSession, interview_id: int) -> dict:
    """Create a lightweight dialog plan from job description and candidate resume.

    The plan guides initial topics and targeted follow-ups to make the interview
    feel tailored before it starts. Stored under analysis.technical_assessment.dialog_plan.
    """
    from sqlalchemy import select as _select
    from src.db.models.job import Job
    from src.db.models.candidate import Candidate
    from src.db.models.candidate_profile import CandidateProfile
    from src.services.nlp import extract_resume_spotlights, make_targeted_question_from_spotlight, extract_requirements_spec

    interview = (
        await session.execute(_select(Interview).where(Interview.id == interview_id))
    ).scalar_one_or_none()
    if not interview:
        return {}

    job = (
        await session.execute(_select(Job).where(Job.id == interview.job_id))
    ).scalar_one_or_none()
    job_desc = (getattr(job, "description", None) or "").strip()

    resume_text = ""
    try:
        cand = (
            await session.execute(_select(Candidate).where(Candidate.id == interview.candidate_id))
        ).scalar_one_or_none()
        if cand:
            profile = (
                await session.execute(_select(CandidateProfile).where(CandidateProfile.candidate_id == cand.id))
            ).scalar_one_or_none()
            if profile and profile.resume_text:
                resume_text = profile.resume_text
    except Exception:
        resume_text = ""

    # Simple topic extraction from job description
    def _job_topics(text: str, max_items: int = 6) -> list[str]:
        import re as _re
        toks = [t.lower() for t in _re.split(r"[^a-zA-ZçğıöşüÇĞİÖŞÜ0-9\\+\\.#]+", text or "") if len(t) >= 3]
        stop = {
            "ve","ile","için","gibi","olan","olarak","çok","az","ile","bir","bu","şu","the","and","for","with","and","our","your",
            "çalışma","ekip","takım","deneyim","deneyimi","sorumluluk","sorumluluklar","görev","pozisyon","çalışacak"
        }
        uniq: list[str] = []
        seen: set[str] = set()
        for t in toks:
            if t in stop:
                continue
            if t in seen:
                continue
            seen.add(t)
            uniq.append(t)
            if len(uniq) >= max_items:
                break
        return uniq

    topics = _job_topics(job_desc)
    # Extract normalized requirements spec from job description (best-effort)
    try:
        req_spec = await extract_requirements_spec(job_desc)
    except Exception:
        req_spec = {"items": []}
    spotlights = extract_resume_spotlights(resume_text, max_items=3) if resume_text else []
    targeted = [make_targeted_question_from_spotlight(s) for s in spotlights]
    first_seed = None
    if topics:
        first_seed = f"Öncelikle {topics[0]} ile ilgili somut bir örneğinizi STAR (Durum, Görev, Eylem, Sonuç) çerçevesinde paylaşır mısınız?"

    plan = {
        "topics": topics,
        "resume_spotlights": spotlights,
        "targeted_questions": targeted,
        "first_question_seed": first_seed,
    }

    await merge_enrichment_into_analysis(session, interview_id, {"dialog_plan": plan, "requirements_spec": req_spec})
    # Also prepare a concrete first question and store on Interview
    try:
        from src.core.gemini import generate_question_robust
        # Internal keywords only to avoid disclosure
        ctx = "Job Description:\n" + (job_desc or "")
        if resume_text:
            try:
                from src.services.dialog import extract_keywords as _ek
                kws = _ek(resume_text)
                if kws:
                    ctx += "\n\nInternal Resume Keywords: " + ", ".join(kws[:30])
            except Exception:
                pass
        res = await generate_question_robust([], ctx, max_questions=7)
        _qval = res.get("question")
        q = _qval.strip() if isinstance(_qval, str) else ""
        # Sanitize: remove any CV/job disclosure
        bad = ["cv", "özgeçmiş", "ilan", "iş tanımı", "linkedin", "http://", "https://"]
        if any(b in q.lower() for b in bad) or not q:
            q = first_seed or "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?"
        iv = (
            await session.execute(_select(Interview).where(Interview.id == interview_id))
        ).scalar_one_or_none()
        if iv:
            iv.prepared_first_question = q
            await session.commit()
    except Exception:
        pass
    return plan


async def precompute_dialog_plan_bg(interview_id: int) -> None:
    """Background helper to precompute and persist dialog plan by interview id."""
    from src.db.session import async_session_factory
    async with async_session_factory() as session:
        try:
            await precompute_dialog_plan(session, interview_id)
        except Exception:
            pass


