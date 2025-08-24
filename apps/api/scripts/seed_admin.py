import asyncio
from sqlalchemy import select
from passlib.hash import bcrypt

from src.db.session import async_session_factory
from src.db.models.user import User


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(User).filter_by(email="admin@example.com"))
        user = result.scalar_one_or_none()
        if user:
            print("exists")
            return
        user = User(
            email="admin@example.com",
            hashed_password=bcrypt.hash("admin123"),
            is_active=True,
            is_superuser=True,
            is_verified=True,
            is_admin=True,
        )
        session.add(user)
        await session.commit()
        print("created")


if __name__ == "__main__":
    asyncio.run(main())


