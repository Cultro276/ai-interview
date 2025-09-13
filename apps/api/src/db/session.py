from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from sqlalchemy.pool import NullPool
from src.db.base import Base

# Async engine & sessionmaker
engine = create_async_engine(settings.database_url, echo=False, future=True, poolclass=NullPool)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a DB session."""
    async with async_session_factory() as session:
        yield session 