from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.services.repositories.conversations import (
    get_candidate_by_token,
    get_interview_by_id,
    has_completed_interview_for_candidate,
    get_message_by_sequence,
    get_last_message,
    get_message_by_content,
    insert_message,
)
from src.db.models.conversation import MessageRole


class ConversationsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_public_message(
        self,
        interview_id: int,
        token: str,
        role: str,
        content: str,
        sequence_number: int,
    ):
        cand = await get_candidate_by_token(self.session, token)
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        if not cand or (cand.expires_at is None) or (cand.expires_at <= now_utc):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
        if await has_completed_interview_for_candidate(self.session, cand.id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview already completed")

        interview = await get_interview_by_id(self.session, interview_id)
        if not interview or interview.candidate_id != cand.id:
            raise HTTPException(status_code=404, detail="Interview not found")

        # Dedup by (interview_id, sequence_number)
        existing = await get_message_by_sequence(self.session, interview_id, sequence_number)
        if existing:
            return existing

        # Ignore very short user messages (noise)
        if role == MessageRole.USER.value and len((content or "").strip()) < 2:
            from src.db.models.conversation import ConversationMessage
            return ConversationMessage(
                id=0,
                interview_id=interview_id,
                role=MessageRole.USER,
                content="",
                timestamp=None,  # type: ignore[arg-type]
                sequence_number=sequence_number,
            )

        # Avoid duplicate consecutive assistant messages
        last = await get_last_message(self.session, interview_id)
        if last and getattr(last.role, "value", str(last.role)) == role and (last.content or "").strip() == (content or "").strip():
            return last

        try:
            return await insert_message(self.session, interview_id, role, content or "", sequence_number)
        except Exception:
            # Ensure session is usable after failed flush/commit
            try:
                await self.session.rollback()
            except Exception:
                pass
            # On race, attempt to return existing record deterministically
            try:
                dup_seq = await get_message_by_sequence(self.session, interview_id, sequence_number)
                if dup_seq:
                    return dup_seq
            except Exception:
                # best-effort only
                pass
            if role == MessageRole.ASSISTANT.value:
                try:
                    dup_msg = await get_message_by_content(self.session, interview_id, content or "")
                    if dup_msg:
                        return dup_msg
                except Exception:
                    pass
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate message")


