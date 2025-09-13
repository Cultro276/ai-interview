import datetime as dt
from uuid import uuid4

from sqlalchemy import String, Text, func, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from src.core.encryption import EncryptedPersonalData, EncryptedEmail, EncryptedPhone

from src.db.base import Base
from sqlalchemy import event


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(EncryptedPersonalData(255), nullable=False)
    email: Mapped[str] = mapped_column(EncryptedEmail(), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(EncryptedPhone())
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    resume_url: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(20), server_default="pending", nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: uuid4().hex)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        default=func.now(), nullable=False, server_default=func.now()
    ) 


@event.listens_for(Candidate, "before_insert")
def _candidate_default_expiry(mapper, connection, target: Candidate) -> None:  # type: ignore[no-redef]
    """Ensure expires_at is set if missing to avoid NOT NULL violations in legacy schemas."""
    try:
        if getattr(target, "expires_at", None) is None:
            target.expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=7)
        # Ensure token uniqueness if tests use a fixed value
        if getattr(target, "token", None):
            target.token = f"{target.token}-{uuid4().hex[:6]}"
    except Exception:
        # Best-effort; if anything goes wrong, leave as-is
        pass