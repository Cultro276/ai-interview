import datetime as dt

from sqlalchemy import String, Text, func, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    default_invite_expiry_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    # Rule-based dialog and analysis configuration
    requirements_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rubric_weights: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        default=func.now(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        default=func.now(), onupdate=func.now(), server_default=func.now()
    ) 