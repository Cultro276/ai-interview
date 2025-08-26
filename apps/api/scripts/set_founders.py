import asyncio
import sys
from sqlalchemy import select

if "/app" not in sys.path:
    sys.path.insert(0, "/app")

from src.db.session import async_session_factory  # type: ignore
from src.db.models.user import User  # type: ignore


FOUNDERS = {"admin@example.com", "owner2@example.com"}


async def main() -> None:
    async with async_session_factory() as session:
        rows = (await session.execute(select(User))).scalars().all()
        for u in rows:
            u.is_superuser = (u.email in FOUNDERS)
        await session.commit()
        print("updated", len(rows))


if __name__ == "__main__":
    asyncio.run(main())


