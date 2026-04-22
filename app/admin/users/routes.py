from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin, oauth2_scheme
from app.auth.schemas import (
    RegisterRequest,
    PasswordChangeRequest,
    UserResponse,
    UserProfileDTO,
    ProfileUpdateRequest,
    UserFilter,
    UserListResponse,
)
from app.admin.users.services import AdminUserService

router = APIRouter(
    prefix="/users",
    tags=["Admin — Users"],
    dependencies=[Depends(oauth2_scheme)],
)


def _get_service(db: AsyncSession = Depends(get_db)) -> AdminUserService:
    return AdminUserService(db)


@router.get("/", response_model=UserListResponse, summary="Список пользователей")
async def list_users(
    login: Optional[str] = None,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    is_active: Optional[bool] = None,
    role: Optional[str] = None,
    position: Optional[str] = None,
    permissions: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    _admin=Depends(require_admin),
    svc: AdminUserService = Depends(_get_service),
):
    filters = UserFilter(
        login=login, full_name=full_name, email=email,
        is_active=is_active, role=role, position=position, permissions=permissions,
    )
    return await svc.list_users(filters=filters, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse, summary="Пользователь по ID")
async def get_user(
    user_id: int,
    _admin=Depends(require_admin),
    svc: AdminUserService = Depends(_get_service),
):
    user = await svc.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.get("/{user_id}/profile", response_model=UserProfileDTO, summary="Профиль")
async def get_profile(
    user_id: int,
    _admin=Depends(require_admin),
    svc: AdminUserService = Depends(_get_service),
):
    profile = await svc.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return profile


@router.put("/{user_id}/profile", response_model=UserProfileDTO, summary="Обновить профиль")
async def update_profile(
    user_id: int,
    request: ProfileUpdateRequest,
    _admin=Depends(require_admin),
    svc: AdminUserService = Depends(_get_service),
):
    return await svc.update_profile(user_id, request)


@router.post("/", response_model=UserResponse, summary="Создать пользователя", status_code=201)
async def create_user(
    request: RegisterRequest,
    _admin=Depends(require_admin),
    svc: AdminUserService = Depends(_get_service),
):
    return await svc.register(request)


@router.post("/{user_id}/toggle-active", summary="Переключить активность")
async def toggle_active(
    user_id: int,
    _admin=Depends(require_admin),
    svc: AdminUserService = Depends(_get_service),
):
    result = await svc.toggle_active(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"user_id": user_id, "action": "toggled"}


@router.post("/{user_id}/change-password", summary="Сменить пароль")
async def change_password(
    user_id: int,
    request: PasswordChangeRequest,
    _admin=Depends(require_admin),
    svc: AdminUserService = Depends(_get_service),
):
    return await svc.change_password(user_id, request)
