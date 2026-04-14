from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.auth.services import AuthService, UserService
from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    PasswordChangeRequest,
    UserResponse,
    UserProfileDTO,
    ProfileUpdateRequest,
    UserFilter,
    UserListResponse,
)


class AdminUserService:
    """Сервис админки для управления пользователями.
    Делегирует вызовы в AuthService и UserService.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._auth_service = AuthService(db)
        self._user_service = UserService(db)

    # --- Auth ---

    async def register(self, request: RegisterRequest) -> UserResponse:
        return await self._auth_service.register(request)

    async def change_password(self, user_id: int, request: PasswordChangeRequest) -> bool:
        return await self._auth_service.change_password(user_id, request)

    async def refresh_token(self, refresh_token: str) -> LoginResponse:
        return await self._auth_service.refresh_token(refresh_token)

    async def logout(self, token: str) -> bool:
        return await self._auth_service.logout(token)

    # --- Users ---

    async def get_by_id(self, user_id: int) -> Optional[UserResponse]:
        return await self._user_service.get_by_id(user_id)

    async def get_by_login(self, login: str) -> Optional[UserResponse]:
        return await self._user_service.get_by_login(login)

    async def list_users(
        self,
        filters: Optional[UserFilter] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> UserListResponse:
        return await self._user_service.list_filtered(filters, skip, limit)

    async def get_profile(self, user_id: int) -> Optional[UserProfileDTO]:
        return await self._user_service.get_profile(user_id)

    async def update_profile(
        self, user_id: int, request: ProfileUpdateRequest
    ) -> UserProfileDTO:
        return await self._user_service.update_profile(user_id, request)

    async def toggle_active(self, user_id: int) -> bool:
        return await self._user_service.toggle_active(user_id)

    async def has_profile(self, user_id: int) -> bool:
        return await self._user_service.has_profile(user_id)
