from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import platform_admin_required
from fastapi import Header
from src.core.config import settings
from pydantic import BaseModel, EmailStr
from passlib.hash import bcrypt
from src.auth import get_user_manager
from src.auth import UserCreate as _UserCreate
from src.auth import get_jwt_strategy
from src.db.session import get_session
from src.db.models.user import User
from src.db.models.job import Job
from src.db.models.candidate import Candidate
from src.db.models.interview import Interview


router = APIRouter(prefix="/internal", tags=["internal-admin"])


def _check_internal_secret(x_internal_secret: str | None = Header(default=None)) -> None:
    if not x_internal_secret or x_internal_secret != settings.internal_admin_secret:
        # Secondary header gate to avoid accidental exposure
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/tenants")
async def list_tenants(session: AsyncSession = Depends(get_session), _: User = Depends(platform_admin_required), __: None = Depends(_check_internal_secret)):
    owners = await session.execute(select(User).where(User.owner_user_id.is_(None)))
    rows = owners.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in rows
    ]


@router.get("/tenant/{owner_id}/overview")
async def tenant_overview(owner_id: int, session: AsyncSession = Depends(get_session), _: User = Depends(platform_admin_required), __: None = Depends(_check_internal_secret)):
    jobs = await session.execute(select(Job).where(Job.user_id == owner_id))
    cands = await session.execute(select(Candidate).where(Candidate.user_id == owner_id))
    interviews = await session.execute(
        select(Interview).join(Job, Interview.job_id == Job.id).where(Job.user_id == owner_id)
    )
    return {
        "jobs": len(jobs.scalars().all()),
        "candidates": len(cands.scalars().all()),
        "interviews": len(interviews.scalars().all()),
    }


@router.delete("/tenant/{owner_id}")
async def delete_tenant(owner_id: int, session: AsyncSession = Depends(get_session), _: User = Depends(platform_admin_required), __: None = Depends(_check_internal_secret)):
    # Soft-delete: deactivate all accounts under owner
    users = (await session.execute(select(User).where((User.id == owner_id) | (User.owner_user_id == owner_id)))).scalars().all()
    if not users:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for u in users:
        u.is_active = False
    await session.commit()
    return {"ok": True, "deactivated": len(users)}


class OwnerCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@router.post("/tenant", status_code=201)
async def create_owner(
    payload: OwnerCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(platform_admin_required),
    __: None = Depends(_check_internal_secret),
    user_manager=Depends(get_user_manager),
):
    # Create an owner account (tenant root). Not platform admin.
    user_in = _UserCreate(
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        is_admin=True,
    )
    user = await user_manager.create(user_in)
    # Explicitly guarantee this owner is NOT a platform admin
    user.is_superuser = False
    await session.commit()
    return {"id": user.id, "email": user.email}


@router.post("/tenant/{owner_id}/reactivate")
async def reactivate_tenant(owner_id: int, session: AsyncSession = Depends(get_session), _: User = Depends(platform_admin_required), __: None = Depends(_check_internal_secret)):
    users = (await session.execute(select(User).where((User.id == owner_id) | (User.owner_user_id == owner_id)))).scalars().all()
    if not users:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for u in users:
        u.is_active = True
    await session.commit()
    return {"ok": True, "reactivated": len(users)}


class ResetPassword(BaseModel):
    new_password: str


@router.post("/tenant/{owner_id}/reset-password")
async def reset_owner_password(owner_id: int, payload: ResetPassword, session: AsyncSession = Depends(get_session), _: User = Depends(platform_admin_required), __: None = Depends(_check_internal_secret)):
    owner = (await session.execute(select(User).where(User.id == owner_id))).scalars().first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    owner.hashed_password = bcrypt.hash(payload.new_password)
    await session.commit()
    return {"ok": True}


@router.post("/tenant/{owner_id}/impersonate")
async def impersonate_owner(owner_id: int, session: AsyncSession = Depends(get_session), _: User = Depends(platform_admin_required), __: None = Depends(_check_internal_secret)):
    owner = (await session.execute(select(User).where(User.id == owner_id))).scalars().first()
    if not owner or not owner.is_active:
        raise HTTPException(status_code=404, detail="Owner not found or inactive")
    token = get_jwt_strategy().write_token(owner)
    return {"access_token": token, "token_type": "bearer"}


