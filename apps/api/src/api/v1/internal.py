from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_, or_, func
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
from src.core.audit import AuditLog


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
            "company_name": u.company_name,
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
@router.get("/tenant/{owner_id}/activity")
async def tenant_activity(
    owner_id: int,
    limit: int = 50,
    start: Optional[str] = None,
    end: Optional[str] = None,
    q: Optional[str] = None,
    etype: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(platform_admin_required),
    __: None = Depends(_check_internal_secret),
):
    # Return last N audit logs for this tenant
    try:
        filters = [AuditLog.tenant_id == owner_id]
        # Parse date range
        from datetime import datetime, timezone
        if start:
            try:
                s = datetime.fromisoformat(start)
                if s.tzinfo is None:
                    s = s.replace(tzinfo=timezone.utc)
                filters.append(AuditLog.timestamp >= s)
            except Exception:
                pass
        if end:
            try:
                e = datetime.fromisoformat(end)
                if e.tzinfo is None:
                    e = e.replace(tzinfo=timezone.utc)
                filters.append(AuditLog.timestamp <= e)
            except Exception:
                pass
        if etype:
            like = f"%{etype.lower()}%"
            filters.append(func.lower(AuditLog.event_type).like(like))
        if q:
            like = f"%{q.lower()}%"
            filters.append(
                or_(
                    func.lower(AuditLog.message).like(like),
                    func.lower(func.coalesce(AuditLog.resource_name, "")).like(like),
                    func.lower(AuditLog.event_type).like(like),
                )
            )
        query = select(AuditLog).where(and_(*filters)).order_by(AuditLog.timestamp.desc()).limit(limit)
        result = await session.execute(query)
        rows = result.scalars().all()
        return [
            {
                "timestamp": getattr(r, "timestamp", None),
                "event_type": getattr(r, "event_type", None),
                "message": getattr(r, "message", None),
            }
            for r in rows
        ]
    except Exception:
        return []


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
    company_name: Optional[str] = None


class TenantUpdate(BaseModel):
    company_name: Optional[str] = None


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
    # Set company name if provided
    if payload.company_name:
        user.company_name = payload.company_name
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


@router.patch("/tenant/{owner_id}")
async def update_tenant(
    owner_id: int,
    payload: TenantUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(platform_admin_required),
    __: None = Depends(_check_internal_secret),
):
    """Update tenant information (currently only company_name)"""
    user = (await session.execute(select(User).where(User.id == owner_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if payload.company_name is not None:
        user.company_name = payload.company_name
    
    await session.commit()
    return {
        "id": user.id,
        "email": user.email,
        "company_name": user.company_name,
        "updated": True
    }


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
    token = await get_jwt_strategy().write_token(owner)
    return {"access_token": token, "token_type": "bearer"}


