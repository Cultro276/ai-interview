from __future__ import annotations

from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.interview import Interview
from src.db.models.job import Job

from src.db.models.conversation import ConversationMessage, InterviewAnalysis


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
        technical_score = 50.0 + min(30.0, len([m for m in user_msgs if any(k in m.content.lower() for k in ["api", "database", "microservice", "docker", "aws"])]) * 10.0)
        cultural_fit_score = 50.0 + min(30.0, len([m for m in user_msgs if any(k in m.content.lower() for k in ["takım", "iletişim", "liderlik", "uyum"])]) * 10.0)
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

    # Upsert analysis
    existing = (
        await session.execute(
            select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id)
        )
    ).scalar_one_or_none()

    if existing:
        existing.overall_score = overall
        existing.summary = summary
        existing.strengths = strengths
        existing.weaknesses = weaknesses
        existing.communication_score = comm
        existing.technical_score = tech
        existing.cultural_fit_score = culture
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
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)
        return analysis


