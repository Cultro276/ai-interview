import asyncio
import sys
from sqlalchemy import select
from passlib.hash import bcrypt

# Ensure we can import 'src' when running as a script from /app/scripts
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

from src.db.session import async_session_factory  # type: ignore
from src.db.models.user import User  # type: ignore


async def main() -> None:
    async with async_session_factory() as session:
        email = "owner2@example.com"
        password = "Owner2!Pass123"
        result = await session.execute(select(User).filter_by(email=email))
        user = result.scalar_one_or_none()
        if user:
            print("exists")
            return
        user = User(
            email=email,
            hashed_password=bcrypt.hash(password),
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
