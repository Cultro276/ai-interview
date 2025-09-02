from datetime import timedelta
from typing import Optional

from fastapi import Depends, Request, HTTPException
from fastapi_users import FastAPIUsers, schemas as fu_schemas
from fastapi_users.authentication import JWTStrategy, AuthenticationBackend, BearerTransport
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from fastapi_users.manager import BaseUserManager
from fastapi_users.password import PasswordHelper
from fastapi_users import IntegerIDMixin
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models.user import User
from src.db.session import get_session

SECRET = settings.jwt_secret

# Pydantic Schemas --------------------------------------------------

class UserRead(fu_schemas.BaseUser[int]):
    first_name: Optional[str]
    last_name: Optional[str]
    is_admin: bool
    owner_user_id: Optional[int] = None
    role: Optional[str] = None
    can_manage_jobs: bool = False
    can_manage_candidates: bool = False
    can_view_interviews: bool = False
    can_manage_members: bool = False


class UserCreate(fu_schemas.BaseUserCreate):
    first_name: Optional[str]
    last_name: Optional[str]
    is_admin: Optional[bool] = False
    owner_user_id: Optional[int] = None
    role: Optional[str] = None
    can_manage_jobs: Optional[bool] = False
    can_manage_candidates: Optional[bool] = False
    can_view_interviews: Optional[bool] = False
    can_manage_members: Optional[bool] = False


class UserUpdate(fu_schemas.BaseUserUpdate):
    first_name: Optional[str]
    last_name: Optional[str]
    is_admin: Optional[bool]
    owner_user_id: Optional[int] = None
    role: Optional[str] = None
    can_manage_jobs: Optional[bool] = None
    can_manage_candidates: Optional[bool] = None
    can_view_interviews: Optional[bool] = None
    can_manage_members: Optional[bool] = None


# Database dependency ----------------------------------------------

async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)


# User manager ------------------------------------------------------

class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} forgot password. Reset token: {token}")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


# Auth backend ------------------------------------------------------

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=60 * 60 * 8)

bearer_transport = BearerTransport(tokenUrl="auth/login")

jwt_backend = AuthenticationBackend(name="jwt", transport=bearer_transport, get_strategy=get_jwt_strategy)

fastapi_users = FastAPIUsers[User, int](
    get_user_manager=get_user_manager,
    auth_backends=[jwt_backend],
)

current_active_user = fastapi_users.current_user(active=True)

# Admin dependency (must be after current_active_user)

async def admin_required(user: User = Depends(current_active_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user 


# --------- Tenant helpers ---------

def get_effective_owner_id(user: User) -> int:
    """Return the tenant owner id for resource scoping.

    - Platform admins operate on their own id.
    - Account owners have owner_user_id = None, so they operate on their id.
    - Assistants have owner_user_id set, so they operate on that owner's id.
    """
    if user.owner_user_id and not user.is_admin:
        return int(user.owner_user_id)
    return int(user.id)


def is_account_owner(user: User) -> bool:
    return (user.owner_user_id is None) or bool(user.is_admin)


def ensure_permission(user: User, *, manage_jobs: bool = False, manage_candidates: bool = False, view_interviews: bool = False, manage_members: bool = False) -> None:
    """Raise 403 if user lacks required permission.

    Owners and platform admins bypass checks. Assistants must have the specific flag.
    """
    if is_account_owner(user):
        return
    if manage_jobs and not bool(user.can_manage_jobs):
        raise HTTPException(status_code=403, detail="Permission 'manage_jobs' required")
    if manage_candidates and not bool(user.can_manage_candidates):
        raise HTTPException(status_code=403, detail="Permission 'manage_candidates' required")
    if view_interviews and not bool(user.can_view_interviews):
        raise HTTPException(status_code=403, detail="Permission 'view_interviews' required")
    if manage_members and not bool(user.can_manage_members):
        raise HTTPException(status_code=403, detail="Permission 'manage_members' required")


# --------- Platform admin (founders) ---------

def platform_admin_required(user: User = Depends(current_active_user)) -> User:
    """Require platform-level admin (fastapi-users superuser flag).

    This is distinct from tenant is_admin which is owner of a company account. Platform admins can
    view/manage all tenants through the internal console.
    """
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Platform admin required")
    return user