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
from app.admin.knowledge_base.services import AdminKnowledgeService

router = APIRouter(
    prefix="/admin/knowledge-base",
    tags=["Admin — Knowledge Base"],
    dependencies=[Depends(oauth2_scheme)],
)


def _get_service(db: AsyncSession = Depends(get_db)) -> AdminKnowledgeService:
    return AdminKnowledgeService(db)


# --- Department ---

@router.get("/departments", response_model=DepartmentListResponse, summary="Список отделов")
async def list_departments(skip: int = 0, limit: int = 100,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    return await svc.list_departments(skip, limit)


@router.post("/departments", response_model=DepartmentResponse, summary="Создать отдел", status_code=201)
async def create_department(data: DepartmentCreate,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    return await svc.create_department(data)


@router.put("/departments/{item_id}", response_model=DepartmentResponse, summary="Обновить отдел")
async def update_department(item_id: int, data: DepartmentCreate,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    item = await svc.update_department(item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Не найден")
    return item


@router.delete("/departments/{item_id}", summary="Удалить отдел")
async def delete_department(item_id: int,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    result = await svc.delete_department(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Не найден")
    return {"id": item_id, "action": "deleted"}


# --- Location ---

@router.get("/locations", response_model=LocationListResponse, summary="Список локаций")
async def list_locations(skip: int = 0, limit: int = 100,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    return await svc.list_locations(skip, limit)


@router.post("/locations", response_model=LocationResponse, summary="Создать локацию", status_code=201)
async def create_location(data: LocationCreate,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    return await svc.create_location(data)


@router.put("/locations/{item_id}", response_model=LocationResponse, summary="Обновить локацию")
async def update_location(item_id: int, data: LocationCreate,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    item = await svc.update_location(item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Не найден")
    return item


@router.delete("/locations/{item_id}", summary="Удалить локацию")
async def delete_location(item_id: int,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    result = await svc.delete_location(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Не найден")
    return {"id": item_id, "action": "deleted"}


# --- Cause Code ---

@router.get("/cause-codes", response_model=CauseCodeListResponse, summary="Список кодов причин")
async def list_cause_codes(skip: int = 0, limit: int = 100,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    return await svc.list_cause_codes(skip, limit)


@router.post("/cause-codes", response_model=CauseCodeResponse, summary="Создать код причины", status_code=201)
async def create_cause_code(data: CauseCodeCreate,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    return await svc.create_cause_code(data)


@router.put("/cause-codes/{item_id}", response_model=CauseCodeResponse, summary="Обновить код причины")
async def update_cause_code(item_id: int, data: CauseCodeCreate,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    item = await svc.update_cause_code(item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Не найден")
    return item


@router.delete("/cause-codes/{item_id}", summary="Удалить код причины")
async def delete_cause_code(item_id: int,
    _admin=Depends(require_admin), svc: AdminKnowledgeService = Depends(_get_service)):
    result = await svc.delete_cause_code(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Не найден")
    return {"id": item_id, "action": "deleted"}
