from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import (
    current_active_user,
    get_effective_owner_id,
    ensure_permission,
    get_user_manager,
)
from src.db.session import get_session
from src.db.models.user import User


router = APIRouter(prefix="/team", tags=["team"])


class TeamMemberRead(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool
    owner_user_id: Optional[int] = None
    role: Optional[str] = None
    can_manage_jobs: bool
    can_manage_candidates: bool
    can_view_interviews: bool
    can_manage_members: bool
    is_active: bool

    model_config = {"from_attributes": True}


class TeamMemberCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    can_manage_jobs: bool = False
    can_manage_candidates: bool = False
    can_view_interviews: bool = False
    can_manage_members: bool = False


class TeamMemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    can_manage_jobs: Optional[bool] = None
    can_manage_candidates: Optional[bool] = None
    can_view_interviews: Optional[bool] = None
    can_manage_members: Optional[bool] = None
    is_active: Optional[bool] = None


@router.get("/members", response_model=List[TeamMemberRead])
async def list_members(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    owner_id = get_effective_owner_id(current_user)
    result = await session.execute(
        select(User).where(or_(User.id == owner_id, User.owner_user_id == owner_id))
    )
    return result.scalars().all()


@router.post("/members", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
async def create_member(
    payload: TeamMemberCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
    user_manager=Depends(get_user_manager),
):
    ensure_permission(current_user, manage_members=True)
    owner_id = get_effective_owner_id(current_user)

    # Prevent duplicate emails within platform (unique enforced at DB level via fastapi-users)
    # Create assistant user under this owner account
    from src.auth import UserCreate as _UserCreate

    user_in = _UserCreate(
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        is_admin=False,
        owner_user_id=owner_id,
        role=payload.role,
        can_manage_jobs=payload.can_manage_jobs,
        can_manage_candidates=payload.can_manage_candidates,
        can_view_interviews=payload.can_view_interviews,
        can_manage_members=payload.can_manage_members,
    )
    try:
        user = await user_manager.create(user_in)
    except Exception as e:
        # FastAPI Users raises on duplicate, invalid password policy, etc.
        raise HTTPException(status_code=400, detail=str(e))
    return user


@router.put("/members/{member_id}", response_model=TeamMemberRead)
async def update_member(
    member_id: int,
    payload: TeamMemberUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    ensure_permission(current_user, manage_members=True)
    owner_id = get_effective_owner_id(current_user)
    member = (
        await session.execute(
            select(User).where(or_(User.id == owner_id, User.owner_user_id == owner_id), User.id == member_id)
        )
    ).scalars().first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.id == owner_id:
        # Do not allow editing owner permissions via team endpoint
        # Allow name/role updates, but block permission fields
        safe_fields = {"first_name", "last_name", "role"}
        for field, value in payload.model_dump(exclude_unset=True).items():
            if field in safe_fields:
                setattr(member, field, value)
        await session.commit()
        await session.refresh(member)
        return member
    # Update editable permission and profile fields for assistants
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    await session.commit()
    await session.refresh(member)
    return member


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    member_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    ensure_permission(current_user, manage_members=True)
    owner_id = get_effective_owner_id(current_user)
    member = (
        await session.execute(
            select(User).where(or_(User.id == owner_id, User.owner_user_id == owner_id), User.id == member_id)
        )
    ).scalars().first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.id == owner_id:
        raise HTTPException(status_code=400, detail="Cannot delete the account owner")
    # Soft-delete by deactivating the user
    member.is_active = False
    await session.commit()
    return None


