from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.models.candidate import Candidate
from src.db.models.conversation import ConversationMessage
from src.db.models.interview import Interview


async def get_candidate_by_token(session: AsyncSession, token: str) -> Optional[Candidate]:
    return (
        await session.execute(select(Candidate).where(Candidate.token == token))
    ).scalar_one_or_none()


async def get_interview_by_id(session: AsyncSession, interview_id: int) -> Optional[Interview]:
    return (
        await session.execute(select(Interview).where(Interview.id == interview_id))
    ).scalar_one_or_none()


async def has_completed_interview_for_candidate(session: AsyncSession, candidate_id: int) -> bool:
    from sqlalchemy import select as _select
    from src.db.models.interview import Interview as _Interview
    row = (
        await session.execute(
            _select(_Interview).where(_Interview.candidate_id == candidate_id, _Interview.status == "completed")
        )
    ).first()
    return row is not None


async def get_message_by_sequence(session: AsyncSession, interview_id: int, sequence_number: int) -> Optional[ConversationMessage]:
    return (
        await session.execute(
            select(ConversationMessage).where(
                ConversationMessage.interview_id == interview_id,
                ConversationMessage.sequence_number == sequence_number,
            )
        )
    ).scalars().first()


async def get_last_message(session: AsyncSession, interview_id: int) -> Optional[ConversationMessage]:
    return (
        await session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.interview_id == interview_id)
            .order_by(ConversationMessage.sequence_number.desc())
        )
    ).scalars().first()


async def get_message_by_content(session: AsyncSession, interview_id: int, content: str) -> Optional[ConversationMessage]:
    return (
        await session.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.interview_id == interview_id,
                ConversationMessage.content == content,
            )
        )
    ).scalars().first()


async def insert_message(
    session: AsyncSession,
    interview_id: int,
    role: str,
    content: str,
    sequence_number: int,
) -> ConversationMessage:
    msg = ConversationMessage(
        interview_id=interview_id,
        role=role,  # type: ignore[arg-type]
        content=(content or "").strip(),
        sequence_number=sequence_number,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


