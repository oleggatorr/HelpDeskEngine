from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin, oauth2_scheme
from app.knowledge_base.schemas import (
    DepartmentCreate, DepartmentResponse, DepartmentListResponse,
    LocationCreate, LocationResponse, LocationListResponse,
    CauseCodeCreate, CauseCodeResponse, CauseCodeListResponse,
)
from app.knowledge_base.services import (
    DepartmentService, LocationService, CauseCodeService,
)

router = APIRouter(
    prefix="/knowledge-base",
    tags=["Knowledge Base"],
    dependencies=[Depends(oauth2_scheme)],
)


def _get_db(db: AsyncSession = Depends(get_db)):
    return db


# ==========================================
# DEPARTMENTS
# ==========================================

@router.get("/departments", response_model=DepartmentListResponse, summary="Список отделов")
async def list_departments(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(_get_db),
):
    svc = DepartmentService(db)
    return await svc.get_all(skip, limit)


@router.get("/departments/{item_id}", response_model=DepartmentResponse, summary="Отдел по ID")
async def get_department(
    item_id: int,
    db: AsyncSession = Depends(_get_db),
):
    svc = DepartmentService(db)
    item = await svc.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Не найден")
    return item


@router.post("/departments", response_model=DepartmentResponse, summary="Создать отдел", status_code=201)
async def create_department(
    data: DepartmentCreate,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
):
    svc = DepartmentService(db)
    return await svc.create(data)


@router.put("/departments/{item_id}", response_model=DepartmentResponse, summary="Обновить отдел")
async def update_department(
    item_id: int, data: DepartmentCreate,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
):
    svc = DepartmentService(db)
    item = await svc.update(item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Не найден")
    return item


@router.delete("/departments/{item_id}", summary="Удалить отдел")
async def delete_department(
    item_id: int,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
):
    svc = DepartmentService(db)
    result = await svc.delete(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Не найден")
    return {"id": item_id, "action": "deleted"}


# ==========================================
# LOCATIONS
# ==========================================

@router.get("/locations", response_model=LocationListResponse, summary="Список локаций")
async def list_locations(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(_get_db),
):
    svc = LocationService(db)
    return await svc.get_all(skip, limit)


@router.get("/locations/{item_id}", response_model=LocationResponse, summary="Локация по ID")
async def get_location(
    item_id: int,
    db: AsyncSession = Depends(_get_db),
):
    svc = LocationService(db)
    item = await svc.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Не найден")
    return item


@router.post("/locations", response_model=LocationResponse, summary="Создать локацию", status_code=201)
async def create_location(
    data: LocationCreate,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
):
    svc = LocationService(db)
    return await svc.create(data)


@router.put("/locations/{item_id}", response_model=LocationResponse, summary="Обновить локацию")
async def update_location(
    item_id: int, data: LocationCreate,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
):
    svc = LocationService(db)
    item = await svc.update(item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Не найден")
    return item


@router.delete("/locations/{item_id}", summary="Удалить локацию")
async def delete_location(
    item_id: int,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
):
    svc = LocationService(db)
    result = await svc.delete(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Не найден")
    return {"id": item_id, "action": "deleted"}


# ==========================================
# CAUSE CODES
# ==========================================

@router.get("/cause-codes", response_model=CauseCodeListResponse, summary="Список кодов причин")
async def list_cause_codes(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(_get_db),
):
    svc = CauseCodeService(db)
    return await svc.get_all(skip, limit)


@router.get("/cause-codes/{item_id}", response_model=CauseCodeResponse, summary="Код причины по ID")
async def get_cause_code(
    item_id: int,
    db: AsyncSession = Depends(_get_db),
):
    svc = CauseCodeService(db)
    item = await svc.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Не найден")
    return item


@router.post("/cause-codes", response_model=CauseCodeResponse, summary="Создать код причины", status_code=201)
async def create_cause_code(
    data: CauseCodeCreate,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
):
    svc = CauseCodeService(db)
    return await svc.create(data)


@router.put("/cause-codes/{item_id}", response_model=CauseCodeResponse, summary="Обновить код причины")
async def update_cause_code(
    item_id: int, data: CauseCodeCreate,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
):
    svc = CauseCodeService(db)
    item = await svc.update(item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Не найден")
    return item


@router.delete("/cause-codes/{item_id}", summary="Удалить код причины")
async def delete_cause_code(
    item_id: int,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
):
    svc = CauseCodeService(db)
    result = await svc.delete(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Не найден")
    return {"id": item_id, "action": "deleted"}
