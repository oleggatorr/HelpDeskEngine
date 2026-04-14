from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge_base.services import (
    DepartmentService,
    LocationService,
    CauseCodeService,
)


class PublicDepartmentService:
    """Публичный слой подразделений."""

    def __init__(self, db: AsyncSession):
        self._service = DepartmentService(db)

    async def get_all(self, *args, **kwargs):
        return await self._service.get_all(*args, **kwargs)

    async def get_by_id(self, *args, **kwargs):
        return await self._service.get_by_id(*args, **kwargs)

    async def create(self, *args, **kwargs):
        return await self._service.create(*args, **kwargs)

    async def update(self, *args, **kwargs):
        return await self._service.update(*args, **kwargs)

    async def delete(self, *args, **kwargs):
        return await self._service.delete(*args, **kwargs)


class PublicLocationService:
    """Публичный слой локаций."""

    def __init__(self, db: AsyncSession):
        self._service = LocationService(db)

    async def get_all(self, *args, **kwargs):
        return await self._service.get_all(*args, **kwargs)

    async def get_by_id(self, *args, **kwargs):
        return await self._service.get_by_id(*args, **kwargs)

    async def create(self, *args, **kwargs):
        return await self._service.create(*args, **kwargs)

    async def update(self, *args, **kwargs):
        return await self._service.update(*args, **kwargs)

    async def delete(self, *args, **kwargs):
        return await self._service.delete(*args, **kwargs)


class PublicCauseCodeService:
    """Публичный слой кодов причин."""

    def __init__(self, db: AsyncSession):
        self._service = CauseCodeService(db)

    async def get_all(self, *args, **kwargs):
        return await self._service.get_all(*args, **kwargs)

    async def get_by_id(self, *args, **kwargs):
        return await self._service.get_by_id(*args, **kwargs)

    async def create(self, *args, **kwargs):
        return await self._service.create(*args, **kwargs)

    async def update(self, *args, **kwargs):
        return await self._service.update(*args, **kwargs)

    async def delete(self, *args, **kwargs):
        return await self._service.delete(*args, **kwargs)
