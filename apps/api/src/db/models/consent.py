import datetime as dt

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class CandidateConsent(Base):
    __tablename__ = "candidate_consents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    accepted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text_version: Mapped[str | None] = mapped_column(String(32), nullable=True)


