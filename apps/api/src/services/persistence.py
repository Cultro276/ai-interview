from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.conversation import ConversationMessage, MessageRole


async def _get_last_message(session: AsyncSession, interview_id: int) -> Optional[ConversationMessage]:
    result = await session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.interview_id == interview_id)
        .order_by(ConversationMessage.sequence_number.desc())
    )
    return result.scalars().first()


async def _get_next_sequence(session: AsyncSession, interview_id: int) -> int:
    last = await _get_last_message(session, interview_id)
    return (last.sequence_number if last else 0) + 1


async def fetch_messages(session: AsyncSession, interview_id: int) -> List[ConversationMessage]:
    """Fetch all messages for interview ordered by sequence."""
    result = await session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.interview_id == interview_id)
        .order_by(ConversationMessage.sequence_number)
    )
    return list(result.scalars().all())


async def persist_user_message(
    session: AsyncSession,
    interview_id: int,
    content: str | None,
) -> Optional[ConversationMessage]:
    """Insert a user message with a fresh sequence number.

    - Skips empty content.
    - Retries once on sequence conflict.
    """
    text = (content or "").strip()
    if not text:
        return None

    # Fast path: if the last message is identical user content, skip (idempotent-ish)
    last = await _get_last_message(session, interview_id)
    if last and getattr(last.role, "value", str(last.role)) == MessageRole.USER.value and (last.content or "").strip() == text:
        return last

    for _ in range(2):
        next_seq = await _get_next_sequence(session, interview_id)
        msg = ConversationMessage(
            interview_id=interview_id,
            role=MessageRole.USER,
            content=text,
            sequence_number=next_seq,
        )
        session.add(msg)
        try:
            await session.commit()
            return msg
        except IntegrityError:
            # Sequence conflict or other concurrency issue; rollback and retry once
            try:
                await session.rollback()
            except Exception:
                pass
        except Exception:
            # Best-effort: rollback and give up
            try:
                await session.rollback()
            except Exception:
                pass
            return None

    # If we reached here, try to return the latest as a best-effort result
    return await _get_last_message(session, interview_id)


async def persist_assistant_message(
    session: AsyncSession,
    interview_id: int,
    content: str | None,
) -> Optional[ConversationMessage]:
    """Insert an assistant message with deduplication and sequence-safe behavior.

    Behaviors:
    - Skip empty content.
    - If the last message is the same assistant content, skip (idempotent).
    - If an assistant message with the same content already exists for this interview
      (unique partial index), return that existing row.
    - Retry once on sequence conflict.
    """
    text = (content or "").strip()
    if not text:
        return None

    # Skip if identical to last assistant message
    last = await _get_last_message(session, interview_id)
    if last and getattr(last.role, "value", str(last.role)) == MessageRole.ASSISTANT.value and (last.content or "").strip() == text:
        return last

    # Check for existing identical assistant content (unique partial index)
    existing_q = await session.execute(
        select(ConversationMessage)
        .where(
            ConversationMessage.interview_id == interview_id,
            ConversationMessage.role == MessageRole.ASSISTANT,
            ConversationMessage.content == text,
        )
        .order_by(ConversationMessage.sequence_number)
    )
    existing = existing_q.scalars().first()
    if existing:
        return existing

    for _ in range(2):
        next_seq = await _get_next_sequence(session, interview_id)
        msg = ConversationMessage(
            interview_id=interview_id,
            role=MessageRole.ASSISTANT,
            content=text,
            sequence_number=next_seq,
        )
        session.add(msg)
        try:
            await session.commit()
            return msg
        except IntegrityError:
            # Either sequence conflict or content unique violation; handle both
            try:
                await session.rollback()
            except Exception:
                pass
            # If unique by content, fetch and return existing
            dup_q = await session.execute(
                select(ConversationMessage)
                .where(
                    ConversationMessage.interview_id == interview_id,
                    ConversationMessage.role == MessageRole.ASSISTANT,
                    ConversationMessage.content == text,
                )
                .order_by(ConversationMessage.sequence_number)
            )
            dup = dup_q.scalars().first()
            if dup:
                return dup
            # else sequence conflict → retry loop
        except Exception:
            # Best-effort: rollback and stop
            try:
                await session.rollback()
            except Exception:
                pass
            return None

    # Final best-effort fetch
    return await _get_last_message(session, interview_id)


