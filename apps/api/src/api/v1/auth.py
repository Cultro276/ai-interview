from fastapi import APIRouter, Depends

from src.auth import fastapi_users, jwt_backend, UserRead, UserCreate, UserUpdate, current_active_user

router = APIRouter(prefix="/auth", tags=["auth"])

router.include_router(
    fastapi_users.get_auth_router(jwt_backend),
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
) 

@router.get("/me", response_model=UserRead)
async def get_me(user=Depends(current_active_user)):
    return user