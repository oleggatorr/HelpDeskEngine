from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services import AuthService, UserService


class PublicAuthService:
    """Публичный слой аутентификации."""

    def __init__(self, db: AsyncSession):
        self._service = AuthService(db)

    async def login(self, *args, **kwargs):
        return await self._service.login(*args, **kwargs)

    async def register(self, *args, **kwargs):
        return await self._service.register(*args, **kwargs)

    async def refresh_token(self, *args, **kwargs):
        return await self._service.refresh_token(*args, **kwargs)

    async def logout(self, *args, **kwargs):
        return await self._service.logout(*args, **kwargs)

    async def change_password(self, *args, **kwargs):
        return await self._service.change_password(*args, **kwargs)


class PublicUserService:
    """Публичный слой пользователей."""

    def __init__(self, db: AsyncSession):
        self._service = UserService(db)

    async def get_by_id(self, *args, **kwargs):
        return await self._service.get_by_id(*args, **kwargs)

    async def get_by_login(self, *args, **kwargs):
        return await self._service.get_by_login(*args, **kwargs)

    async def get_all(self, *args, **kwargs):
        return await self._service.get_all(*args, **kwargs)

    async def list_filtered(self, *args, **kwargs):
        return await self._service.list_filtered(*args, **kwargs)

    async def get_profile(self, *args, **kwargs):
        return await self._service.get_profile(*args, **kwargs)

    async def update_profile(self, *args, **kwargs):
        return await self._service.update_profile(*args, **kwargs)

    async def toggle_active(self, *args, **kwargs):
        return await self._service.toggle_active(*args, **kwargs)

    async def has_profile(self, *args, **kwargs):
        return await self._service.has_profile(*args, **kwargs)
