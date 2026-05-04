from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.schemas import AppPermissionRequest, PermissionModifyRequest
from app.auth.permission_service import PermissionService
from app.auth.models import *


from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.auth.public_services import PublicAuthService, PublicUserService
from app.auth.models import User
from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
    PasswordChangeRequest,
    UserProfileDTO,
    ProfileUpdateRequest,
    UserFilter,
    UserListResponse,
)

router = APIRouter()


def _get_public_auth_service(db: AsyncSession = Depends(get_db)) -> PublicAuthService:
    return PublicAuthService(db)


def _get_public_user_service(db: AsyncSession = Depends(get_db)) -> PublicUserService:
    return PublicUserService(db)


# ==========================================
# AUTH ROUTES (public)
# ==========================================

@router.post("/login", response_model=LoginResponse, summary="Вход в систему")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    service: PublicAuthService = Depends(_get_public_auth_service),
):
    request = LoginRequest(login=form.username, password=form.password)
    return await service.login(request)


@router.post(
    "/register",
    response_model=UserResponse,
    summary="Регистрация",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    service: PublicAuthService = Depends(_get_public_auth_service),
):
    return await service.register(request)


@router.post("/refresh", response_model=LoginResponse, summary="Обновить токен")
async def refresh(
    refresh_token: str,
    service: PublicAuthService = Depends(_get_public_auth_service),
):
    return await service.refresh_token(refresh_token)


# ==========================================
# AUTH ROUTES (protected)
# ==========================================

@router.post("/logout", summary="Выход из системы")
async def logout(
    token: str,
    current_user: User = Depends(get_current_user),
    service: PublicAuthService = Depends(_get_public_auth_service),
):
    result = await service.logout(token)
    return {"success": result}


@router.post("/change-password", summary="Смена пароля")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    service: PublicAuthService = Depends(_get_public_auth_service),
):
    result = await service.change_password(current_user.id, request)
    return {"success": result}


# ==========================================
# USER ROUTES
# ==========================================

@router.get("/users/me", response_model=UserResponse, summary="Текущий пользователь")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    user = await service.get_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.get("/users/me/profile", response_model=UserProfileDTO, summary="Профиль текущего пользователя")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    profile = await service.get_profile(current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return profile


@router.put("/users/me/profile", response_model=UserProfileDTO, summary="Обновить профиль")
async def update_current_user_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """
    🔥 Теперь permissions принимается как JSON:

    {
        "permissions": {
            "app1": ["read", "write"],
            "app2": ["read"]
        }
    }
    """
    return await service.update_profile(current_user.id, request)


@router.get("/users/{user_id}", response_model=UserResponse, summary="Получить пользователя")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.get("/users/login/{login}", response_model=UserResponse, summary="Поиск по логину")
async def get_user_by_login(
    login: str,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    user = await service.get_by_login(login)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.get("/users", response_model=UserListResponse, summary="Список пользователей")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    filters: UserFilter = Depends(),
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """
    🔥 Фильтр permissions теперь JSON:

    Пример:
    ?permissions={"app1":["read"]}
    """
    return await service.list_filtered(filters, skip=skip, limit=limit)


@router.get("/users/{user_id}/profile", response_model=UserProfileDTO, summary="Профиль пользователя")
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    profile = await service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return profile


@router.patch("/users/{user_id}/toggle-active", summary="Переключить активность")
async def toggle_user_active(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    result = await service.toggle_active(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"success": result}


@router.get("/users/{user_id}/has-profile", summary="Есть ли профиль")
async def check_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    result = await service.has_profile(user_id)
    return {"has_profile": result}


@router.get("/", summary="Auth модуль")
async def auth_root():
    return {"module": "auth"}


"""
_________________________________---------------
"""


@router.post("/users/{user_id}/permissions/app", summary="Добавить приложение")
async def add_app(
    user_id: int,
    request: AppPermissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 🔐 Проверка: только админ может управлять правами
    PermissionService.require_role(current_user, UserRole.ADMIN)
    
    service = PermissionService(db)
    profile = await service.db.get(UserProfile, user_id)  # или через UserService
    
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль пользователя не найден")
    
    profile.permissions = service.add_app(profile, request.app)
    print(profile.permissions)

    await db.commit()
    await db.refresh(profile)
    print(profile.permissions)
    return {"permissions": profile.permissions}


@router.delete("/users/{user_id}/permissions/app", summary="Удалить приложение")
async def remove_app(
    user_id: int,
    request: AppPermissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    
    service = PermissionService(db)
    profile = await service.db.get(UserProfile, user_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль пользователя не найден")
    
    permissions = service.remove_app(profile, request.app)
    
    await db.commit()
    await db.refresh(profile)
    
    return {"permissions": permissions}


@router.post("/users/{user_id}/permissions", summary="Добавить права")
async def add_permissions(
    user_id: int,
    request: PermissionModifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    
    service = PermissionService(db)
    profile = await service.db.get(UserProfile, user_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль пользователя не найден")
    
    permissions = service.add_permissions(profile, request.app, request.permissions)
    
    await db.commit()
    await db.refresh(profile)
    
    return {"permissions": permissions}


@router.delete("/users/{user_id}/permissions", summary="Удалить права")
async def remove_permissions(
    user_id: int,
    request: PermissionModifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    PermissionService.require_role(current_user, UserRole.ADMIN)
    
    service = PermissionService(db)
    profile = await service.db.get(UserProfile, user_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль пользователя не найден")
    
    permissions = service.remove_permissions(profile, request.app, request.permissions)
    
    await db.commit()
    await db.refresh(profile)
    
    return {"permissions": permissions}