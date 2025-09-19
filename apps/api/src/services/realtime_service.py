from __future__ import annotations

from typing import Optional, Tuple, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.models.interview import Interview
from src.db.models.conversation import ConversationMessage
from src.services.prompt_registry import RECRUITER_PERSONA, build_role_guidance_block


async def _get_job_company(
    session: AsyncSession,
    interview: Interview,
) -> Tuple[Optional[str], str, Optional[str]]:
    job_title: Optional[str] = None
    job_desc: str = ""
    company_name: Optional[str] = None
    try:
        from src.db.models.job import Job
        from src.db.models.user import User
        job = (
            await session.execute(select(Job).where(Job.id == interview.job_id))
        ).scalar_one_or_none()
        job_title = getattr(job, "title", None)
        job_desc = getattr(job, "description", "") or ""
        if job:
            user = (await session.execute(select(User).where(User.id == job.user_id))).scalar_one_or_none()
            company_name = getattr(user, "company_name", None)
    except Exception:
        pass
    return job_title, job_desc, company_name


def build_realtime_instructions(job_title: Optional[str], company_name: Optional[str]) -> str:
    instructions = (
        "You are a professional HR interviewer conducting a natural Turkish voice conversation. "
        "Speak concisely, one question at a time; do not narrate system states. "
        "Be warm and neutral, avoid gendered language, use 'siz'. "
    )
    if company_name:
        instructions += f"Company: {company_name}. "
    if job_title:
        instructions += f"Role: {job_title}. "
    return instructions


async def build_sse_system_and_messages(
    session: AsyncSession,
    interview: Interview,
    history: List[Dict[str, str]],
) -> Tuple[str, List[Dict[str, str]]]:
    job_title, job_desc, company_name = await _get_job_company(session, interview)

    role_block = build_role_guidance_block(job_desc) if job_desc else ""
    system_parts = [
        RECRUITER_PERSONA,
        (
            "You are a professional HR interviewer conducting a natural Turkish voice conversation. "
            "Speak concisely and ask exactly ONE question at a time. Do not narrate system states. "
            "Avoid gendered language; use 'siz'. If the last user message is empty or too short, "
            "politely re-ask the same question more slowly in one sentence."
        ),
    ]
    if company_name:
        system_parts.append(f"Company: {company_name}.")
    if job_title:
        system_parts.append(f"Role: {job_title}.")
    if role_block:
        system_parts.append(role_block)
    system_parts.append(
        "Output only the next interviewer question in Turkish. Do not add explanations or labels."
    )
    system_content = "\n\n".join([p for p in system_parts if p])
    messages = (
        [{"role": "system", "content": system_content}] +
        [{"role": h["role"], "content": h["content"]} for h in history]
    )
    return system_content, messages


async def get_brief_realtime_instructions(
    session: AsyncSession,
    interview: Interview,
) -> str:
    job_title, _job_desc, company_name = await _get_job_company(session, interview)
    return build_realtime_instructions(job_title, company_name)


