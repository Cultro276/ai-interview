import datetime as dt
from uuid import uuid4

from sqlalchemy import String, Text, func, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from src.core.encryption import EncryptedPersonalData, EncryptedEmail, EncryptedPhone

from src.db.base import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(EncryptedPersonalData(255), nullable=False)
    email: Mapped[str] = mapped_column(EncryptedEmail(), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(EncryptedPhone())
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    resume_url: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(20), server_default="pending", nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: uuid4().hex)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        default=func.now(), nullable=False, server_default=func.now()
    ) 