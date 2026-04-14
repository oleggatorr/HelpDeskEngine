from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin, oauth2_scheme
from app.reports.documents.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse,
    DocumentFilter,
)
from app.admin.reports.services import AdminDocumentService

router = APIRouter(
    prefix="/admin/documents",
    tags=["Admin — Documents"],
    dependencies=[Depends(oauth2_scheme)],
)


def _get_service(db: AsyncSession = Depends(get_db)) -> AdminDocumentService:
    return AdminDocumentService(db)


@router.get("/", response_model=DocumentListResponse, summary="Список документов")
async def list_documents(
    track_id: Optional[str] = None,
    created_by: Optional[int] = None,
    status: Optional[str] = None,
    doc_type_id: Optional[int] = None,
    current_stage: Optional[str] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    sort_by: Optional[str] = "id",
    sort_order: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 100,
    _admin=Depends(require_admin),
    svc: AdminDocumentService = Depends(_get_service),
):
    filters = DocumentFilter(
        track_id=track_id,
        created_by=created_by,
        status=status,
        doc_type_id=doc_type_id,
        current_stage=current_stage,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await svc.list_documents(filters=filters, skip=skip, limit=limit)


@router.get("/{doc_id}", response_model=DocumentResponse, summary="Документ по ID")
async def get_document(
    doc_id: int,
    _admin=Depends(require_admin),
    svc: AdminDocumentService = Depends(_get_service),
):
    doc = await svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return doc


@router.get("/track/{track_id}", response_model=DocumentResponse, summary="Документ по трек-номеру")
async def get_document_by_track(
    track_id: str,
    _admin=Depends(require_admin),
    svc: AdminDocumentService = Depends(_get_service),
):
    doc = await svc.get_by_track_id(track_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return doc


@router.post("/", response_model=DocumentResponse, summary="Создать документ", status_code=201)
async def create_document(
    data: DocumentCreate,
    _admin=Depends(require_admin),
    svc: AdminDocumentService = Depends(_get_service),
):
    return await svc.create_document(data)


@router.put("/{doc_id}", response_model=DocumentResponse, summary="Обновить документ")
async def update_document(
    doc_id: int, data: DocumentUpdate,
    _admin=Depends(require_admin),
    svc: AdminDocumentService = Depends(_get_service),
):
    doc = await svc.update_document(doc_id, data)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return doc


@router.delete("/{doc_id}", summary="Удалить документ")
async def delete_document(
    doc_id: int,
    _admin=Depends(require_admin),
    svc: AdminDocumentService = Depends(_get_service),
):
    result = await svc.delete_document(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return {"id": doc_id, "action": "deleted"}
