import datetime as dt
from typing import Optional

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable

from src.db.base import Base
from sqlalchemy import String, Integer, Boolean, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"

    # Explicit PK to satisfy SQLAlchemy mapper in Alembic env
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[override]

    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        default=func.now(), nullable=False, server_default=func.now()
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    # Tenant ownership: if set, this user belongs to the account owned by owner_user_id
    owner_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Simple permission toggles for assistants
    can_manage_jobs: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    can_manage_candidates: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    can_view_interviews: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    can_manage_members: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)