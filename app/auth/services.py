from abc import ABC, abstractmethod
from typing import Optional
from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    PasswordChangeRequest,
    UserResponse,
    UserProfileDTO,
    ProfileUpdateRequest,
    UserListResponse,
)


# ==========================================
# AUTH SERVICE
# ==========================================

class IAuthService(ABC):
    """
    Сервис аутентификации.
    Вход: LoginRequest, RegisterRequest, PasswordChangeRequest.
    Выход: LoginResponse, bool.
    """

    @abstractmethod
    async def login(self, request: LoginRequest) -> LoginResponse:
        """Вход: LoginRequest. Выход: LoginResponse. Комментарий: проверка учетных данных, выдача JWT."""
        ...

    @abstractmethod
    async def register(self, request: RegisterRequest) -> UserResponse:
        """Вход: RegisterRequest. Выход: UserResponse. Комментарий: создание нового пользователя."""
        ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> LoginResponse:
        """Вход: refresh_token. Выход: LoginResponse. Комментарий: обновление access_token."""
        ...

    @abstractmethod
    async def logout(self, token: str) -> bool:
        """Вход: token. Выход: bool. Комментарий: инвалидация токена."""
        ...

    @abstractmethod
    async def change_password(self, user_id: int, request: PasswordChangeRequest) -> bool:
        """Вход: user_id, PasswordChangeRequest. Выход: bool. Комментарий: смена пароля."""
        ...


# ==========================================
# USER SERVICE
# ==========================================

class IUserService(ABC):
    """
    Сервис пользователей.
    Вход: ID, фильтры, ProfileUpdateRequest.
    Выход: UserResponse, UserProfileDTO, UserListResponse.
    """

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[UserResponse]:
        """Вход: user_id. Выход: Optional[UserResponse]. Комментарий: получение пользователя по ID."""
        ...

    @abstractmethod
    async def get_by_login(self, login: str) -> Optional[UserResponse]:
        """Вход: login. Выход: Optional[UserResponse]. Комментарий: поиск по логину."""
        ...

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> UserListResponse:
        """Вход: skip, limit. Выход: UserListResponse. Комментарий: пагинированный список."""
        ...

    @abstractmethod
    async def get_profile(self, user_id: int) -> Optional[UserProfileDTO]:
        """Вход: user_id. Выход: Optional[UserProfileDTO]. Комментарий: получение профиля."""
        ...

    @abstractmethod
    async def update_profile(self, user_id: int, request: ProfileUpdateRequest) -> UserProfileDTO:
        """Вход: user_id, ProfileUpdateRequest. Выход: UserProfileDTO. Комментарий: обновление роли, должности, допусков."""
        ...

    @abstractmethod
    async def toggle_active(self, user_id: int) -> bool:
        """Вход: user_id. Выход: bool. Комментарий: активация/деактивация пользователя."""
        ...

    @abstractmethod
    async def has_profile(self, user_id: int) -> bool:
        """Вход: user_id. Выход: bool. Комментарий: проверка наличия профиля у пользователя."""
        ...
