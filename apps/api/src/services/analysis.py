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
        "question_count": len([m for m in messages if m.role.value == "assistant"]) if 'messages' in locals() else None,
        "answer_count": len([m for m in messages if m.role.value == "user"]) if 'messages' in locals() else None,
        "avg_answer_length_words": round((sum(len(m.content.split()) for m in messages if m.role.value == "user") / max(1, len([m for m in messages if m.role.value == "user"]))), 1) if 'messages' in locals() else None,
        "filler_word_count": filler_count if 'filler_count' in locals() else None,
        "top_keywords": sorted(list({k for m in (messages or []) if m.role.value == "user" for k in (["api","database","microservice","docker","aws","takım","iletişim","liderlik","uyum"]) if k in m.content.lower()})) if 'messages' in locals() else [],
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
    # Merge keys conservatively
    for k in ("soft_skills", "speech", "vision", "llm_summary"):
        if k in enrichment and enrichment[k]:
            blob[k] = enrichment[k]
    analysis.technical_assessment = json.dumps(blob, ensure_ascii=False)
    await session.commit()
    await session.refresh(analysis)
    return analysis


async def enrich_with_job_and_hr(
    session: AsyncSession,
    interview_id: int,
) -> None:
    """Enrich analysis with HR criteria scores and job-fit summary."""
    from sqlalchemy import select as _select
    from src.db.models.job import Job
    from src.db.models.candidate import Candidate
    from src.db.models.candidate_profile import CandidateProfile
    from src.services.nlp import assess_hr_criteria, assess_job_fit, opinion_on_candidate

    interview = (
        await session.execute(_select(Interview).where(Interview.id == interview_id))
    ).scalar_one_or_none()
    if not interview:
        return
    job = (
        await session.execute(_select(Job).where(Job.id == interview.job_id))
    ).scalar_one_or_none()
    job_desc = getattr(job, "description", None) or ""

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

    # Trim overly long transcripts for safety
    transcript_text = (interview.transcript_text or "")
    if len(transcript_text) > 50000:
        transcript_text = transcript_text[:50000]
    if not transcript_text.strip():
        # Fallback to assembling from conversation messages (user turns)
        msgs = (
            await session.execute(
                _select(ConversationMessage)
                .where(ConversationMessage.interview_id == interview_id)
                .order_by(ConversationMessage.sequence_number)
            )
        ).scalars().all()
        if msgs:
            transcript_text = "\n\n".join(
                [m.content.strip() for m in msgs if m.role.value == "user" and m.content.strip()]
            )
    if not transcript_text.strip():
        return

    hr = await assess_hr_criteria(transcript_text)
    fit = await assess_job_fit(job_desc, transcript_text, resume_text)
    op = await opinion_on_candidate(job_desc, transcript_text, resume_text)

    await merge_enrichment_into_analysis(session, interview_id, {
        "hr_criteria": hr,
        "job_fit": fit,
        "ai_opinion": op,
    })


