import datetime as dt

from sqlalchemy import JSON, Text, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class InterviewScorecard(Base):
    __tablename__ = "interview_scorecards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    competency_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


