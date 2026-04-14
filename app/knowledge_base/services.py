from typing import Optional, List, Generic, TypeVar
from fastapi import HTTPException, status
from sqlalchemy import select, func, update as sa_update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge_base.models import Department, Location, CauseCode
from app.knowledge_base.schemas import (
    DepartmentCreate, DepartmentResponse, DepartmentListResponse,
    LocationCreate, LocationResponse, LocationListResponse,
    CauseCodeCreate, CauseCodeResponse, CauseCodeListResponse,
)


# ==========================================
# GENERIC CRUD FOR DICTIONARIES
# ==========================================

T = TypeVar("T")


class DictCRUD:
    """Базовый CRUD для справочников."""

    def __init__(self, db: AsyncSession, model, response_cls, list_cls):
        self.db = db
        self.model = model
        self.response_cls = response_cls
        self.list_cls = list_cls

    async def get_all(self, skip: int = 0, limit: int = 100):
        count_result = await self.db.execute(select(func.count(self.model.id)))
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(self.model).order_by(self.model.id).offset(skip).limit(limit)
        )
        items = result.scalars().all()

        return self.list_cls(
            items=[self.response_cls.model_validate(i) for i in items],
            total=total,
        )

    async def get_by_id(self, item_id: int):
        result = await self.db.execute(
            select(self.model).where(self.model.id == item_id)
        )
        item = result.scalar_one_or_none()
        return self.response_cls.model_validate(item) if item else None

    async def create(self, data):
        item = self.model(**data.model_dump())
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return self.response_cls.model_validate(item)

    async def update(self, item_id: int, data) -> Optional[object]:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(item_id)

        await self.db.execute(
            sa_update(self.model).where(self.model.id == item_id).values(**update_data)
        )
        await self.db.commit()
        return await self.get_by_id(item_id)

    async def delete(self, item_id: int) -> bool:
        result = await self.db.execute(
            delete(self.model).where(self.model.id == item_id)
        )
        await self.db.commit()
        return result.rowcount > 0


# ==========================================
# SPECIFIC SERVICES
# ==========================================

class DepartmentService(DictCRUD):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Department, DepartmentResponse, DepartmentListResponse)


class LocationService(DictCRUD):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Location, LocationResponse, LocationListResponse)


class CauseCodeService(DictCRUD):
    def __init__(self, db: AsyncSession):
        super().__init__(db, CauseCode, CauseCodeResponse, CauseCodeListResponse)
