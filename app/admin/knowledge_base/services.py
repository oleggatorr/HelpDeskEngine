from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.knowledge_base.services import (
    DepartmentService, LocationService, CauseCodeService,
)
from app.knowledge_base.schemas import (
    DepartmentCreate, DepartmentResponse, DepartmentListResponse,
    LocationCreate, LocationResponse, LocationListResponse,
    CauseCodeCreate, CauseCodeResponse, CauseCodeListResponse,
)


class AdminKnowledgeService:
    """Сервис админки для справочников."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._dept_svc = DepartmentService(db)
        self._loc_svc = LocationService(db)
        self._cause_svc = CauseCodeService(db)

    # --- Department ---
    async def list_departments(self, skip: int = 0, limit: int = 100) -> DepartmentListResponse:
        return await self._dept_svc.get_all(skip, limit)

    async def get_department(self, item_id: int) -> Optional[DepartmentResponse]:
        return await self._dept_svc.get_by_id(item_id)

    async def create_department(self, data: DepartmentCreate) -> DepartmentResponse:
        return await self._dept_svc.create(data)

    async def update_department(self, item_id: int, data: DepartmentCreate) -> Optional[DepartmentResponse]:
        return await self._dept_svc.update(item_id, data)

    async def delete_department(self, item_id: int) -> bool:
        return await self._dept_svc.delete(item_id)

    # --- Location ---
    async def list_locations(self, skip: int = 0, limit: int = 100) -> LocationListResponse:
        return await self._loc_svc.get_all(skip, limit)

    async def get_location(self, item_id: int) -> Optional[LocationResponse]:
        return await self._loc_svc.get_by_id(item_id)

    async def create_location(self, data: LocationCreate) -> LocationResponse:
        return await self._loc_svc.create(data)

    async def update_location(self, item_id: int, data: LocationCreate) -> Optional[LocationResponse]:
        return await self._loc_svc.update(item_id, data)

    async def delete_location(self, item_id: int) -> bool:
        return await self._loc_svc.delete(item_id)

    # --- Cause Code ---
    async def list_cause_codes(self, skip: int = 0, limit: int = 100) -> CauseCodeListResponse:
        return await self._cause_svc.get_all(skip, limit)

    async def get_cause_code(self, item_id: int) -> Optional[CauseCodeResponse]:
        return await self._cause_svc.get_by_id(item_id)

    async def create_cause_code(self, data: CauseCodeCreate) -> CauseCodeResponse:
        return await self._cause_svc.create(data)

    async def update_cause_code(self, item_id: int, data: CauseCodeCreate) -> Optional[CauseCodeResponse]:
        return await self._cause_svc.update(item_id, data)

    async def delete_cause_code(self, item_id: int) -> bool:
        return await self._cause_svc.delete(item_id)
