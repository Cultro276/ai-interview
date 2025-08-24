import datetime as dt
from typing import Optional

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable

from src.db.base import Base
from sqlalchemy import String, Integer, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column


class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"

    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        default=func.now(), nullable=False, server_default=func.now()
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)