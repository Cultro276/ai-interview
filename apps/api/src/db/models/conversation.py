import datetime as dt
from enum import Enum

from sqlalchemy import String, Text, func, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class MessageRole(str, Enum):
    ASSISTANT = "assistant"  # AI soruları
    USER = "user"           # Aday cevapları
    SYSTEM = "system"       # Sistem mesajları


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint("interview_id", "sequence_number", name="uq_convo_interview_seq"),
        Index("ix_convo_interview_seq", "interview_id", "sequence_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Actual text content
    timestamp: Mapped[dt.datetime] = mapped_column(
        default=func.now(), nullable=False, server_default=func.now()
    )
    sequence_number: Mapped[int] = mapped_column(nullable=False)  # Order in conversation
    
    # Relationships
    interview = relationship("Interview", back_populates="conversation_messages")


class InterviewAnalysis(Base):
    __tablename__ = "interview_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # AI Analysis Results
    overall_score: Mapped[float | None] = mapped_column(nullable=True)  # 0-100 score
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array or text
    weaknesses: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array or text
    technical_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    communication_score: Mapped[float | None] = mapped_column(nullable=True)  # 0-100
    technical_score: Mapped[float | None] = mapped_column(nullable=True)  # 0-100
    cultural_fit_score: Mapped[float | None] = mapped_column(nullable=True)  # 0-100
    
    # Metadata
    analysis_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)  # What prompt was used
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Which AI model
    created_at: Mapped[dt.datetime] = mapped_column(
        default=func.now(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        default=func.now(), onupdate=func.now(), server_default=func.now()
    )
    
    # Relationships
    interview = relationship("Interview", back_populates="analysis") 