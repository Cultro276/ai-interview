import asyncio
import sys
sys.path.append('/app')

from src.db.session import async_session_factory
from sqlalchemy import select
from src.db.models.user import User

async def check_user():
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == 'admin@example.com'))
        user = result.scalar_one_or_none()
        if user:
            print(f'User found: email={user.email}')
            print(f'is_active: {user.is_active}')
            print(f'is_verified: {user.is_verified}') 
            print(f'is_admin: {user.is_admin}')
            print(f'is_superuser: {user.is_superuser}')
        else:
            print('User not found!')

if __name__ == "__main__":
    asyncio.run(check_user())
