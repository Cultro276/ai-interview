import datetime as dt

from sqlalchemy import ForeignKey, String, func, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    audio_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Persisted transcript fields (replace prior in-memory usage)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prepared_first_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        default=func.now(), nullable=False, server_default=func.now()
    )
    
    # Relationships
    conversation_messages = relationship("ConversationMessage", back_populates="interview", cascade="all, delete-orphan")
    analysis = relationship("InterviewAnalysis", back_populates="interview", uselist=False, cascade="all, delete-orphan") 