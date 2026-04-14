from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

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
# AUTH ROUTES (public — без авторизации)
# ==========================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Вход в систему",
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    service: PublicAuthService = Depends(_get_public_auth_service),
):
    """
    Вход по логину и паролю.
    Для Swagger: используйте login как username, пароль как password.
    """
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
    """Регистрация нового пользователя."""
    return await service.register(request)


@router.post(
    "/refresh",
    response_model=LoginResponse,
    summary="Обновить токен",
)
async def refresh(
    refresh_token: str,
    service: PublicAuthService = Depends(_get_public_auth_service),
):
    """Обновление access_token по refresh_token."""
    return await service.refresh_token(refresh_token)


# ==========================================
# AUTH ROUTES (требуется авторизация)
# ==========================================

@router.post(
    "/logout",
    summary="Выход из системы",
)
async def logout(
    token: str,
    current_user: User = Depends(get_current_user),
    service: PublicAuthService = Depends(_get_public_auth_service),
):
    """Выход и инвалидация токена."""
    result = await service.logout(token)
    return {"success": result}


@router.post(
    "/change-password",
    summary="Смена пароля",
)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    service: PublicAuthService = Depends(_get_public_auth_service),
):
    """Смена пароля текущего пользователя."""
    result = await service.change_password(current_user.id, request)
    return {"success": result}


# ==========================================
# USER ROUTES (требуется авторизация)
# ==========================================

@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Текущий пользователь",
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """Получить информацию о текущем пользователе."""
    user = await service.get_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user


@router.get(
    "/users/me/profile",
    response_model=UserProfileDTO,
    summary="Профиль текущего пользователя",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """Получить профиль текущего пользователя."""
    profile = await service.get_profile(current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    return profile


@router.put(
    "/users/me/profile",
    response_model=UserProfileDTO,
    summary="Обновить профиль текущего пользователя",
)
async def update_current_user_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """Обновить роль, должность, допуски текущего пользователя."""
    return await service.update_profile(current_user.id, request)


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Получить пользователя по ID",
)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """Получить пользователя по ID."""
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user


@router.get(
    "/users/login/{login}",
    response_model=UserResponse,
    summary="Получить пользователя по логину",
)
async def get_user_by_login(
    login: str,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """Поиск пользователя по логину."""
    user = await service.get_by_login(login)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="Список пользователей",
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    filters: UserFilter = Depends(),
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """Пагинированный список пользователей с фильтрами."""
    return await service.list_filtered(filters, skip=skip, limit=limit)


@router.get(
    "/users/{user_id}/profile",
    response_model=UserProfileDTO,
    summary="Получить профиль пользователя",
)
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """Получить профиль пользователя."""
    profile = await service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    return profile


@router.patch(
    "/users/{user_id}/toggle-active",
    summary="Активировать/деактивировать пользователя",
)
async def toggle_user_active(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """Переключение статуса активности пользователя."""
    result = await service.toggle_active(user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return {"success": result}


@router.get(
    "/users/{user_id}/has-profile",
    summary="Проверить наличие профиля",
)
async def check_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicUserService = Depends(_get_public_user_service),
):
    """Проверка наличия профиля у пользователя."""
    result = await service.has_profile(user_id)
    return {"has_profile": result}


@router.get("/", summary="Auth модуль")
async def auth_root():
    return {"module": "auth"}
