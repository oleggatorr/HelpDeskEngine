from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.reports.documents.public_services.document import PublicDocumentService
from app.reports.documents.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    DocumentFilter,
    DocumentStatus,
    DocumentPriority,
    DocumentStage,
    DocumentLanguage,
)
from app.auth.models import User

router = APIRouter()


def _get_doc_service(db: AsyncSession = Depends(get_db)) -> PublicDocumentService:
    return PublicDocumentService(db)


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="Список документов",
)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    filters: DocumentFilter = Depends(),
    service: PublicDocumentService = Depends(_get_doc_service),
    current_user: User = Depends(get_current_user),
):
    """Пагинированный список документов с фильтрами и сортировкой."""
    return await service.list_filtered(
        skip=skip,
        limit=limit,
        track_id=filters.track_id,
        status=filters.status,
        doc_type_id=filters.doc_type_id,
        current_stage=filters.current_stage,
        created_by=filters.created_by,
        assigned_to=filters.assigned_to,
        created_from=filters.created_from,
        created_to=filters.created_to,
        sort_by=filters.sort_by,
        sort_order=filters.sort_order,
    )


@router.get(
    "/documents/track/{track_id}",
    response_model=DocumentResponse,
    summary="Документ по трек-номеру",
)
async def get_document_by_track(
    track_id: str,
    service: PublicDocumentService = Depends(_get_doc_service),
    current_user: User = Depends(get_current_user),
):
    """Получить документ по трек-номеру (XXX-XXXX-XXX)."""
    doc = await service.get_by_track_id(track_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    return doc


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentResponse,
    summary="Документ по ID",
)
async def get_document(
    doc_id: int,
    service: PublicDocumentService = Depends(_get_doc_service),
    current_user: User = Depends(get_current_user),
):
    """Получить документ по ID."""
    doc = await service.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    return doc


@router.post(
    "/documents",
    response_model=DocumentResponse,
    summary="Создать документ",
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    request: DocumentCreate,
    current_user: User = Depends(get_current_user),
    service: PublicDocumentService = Depends(_get_doc_service),
):
    """Создать новый документ."""
    return await service.create(request)


@router.put(
    "/documents/{doc_id}",
    response_model=DocumentResponse,
    summary="Обновить документ",
)
async def update_document(
    doc_id: int,
    request: DocumentUpdate,
    service: PublicDocumentService = Depends(_get_doc_service),
    current_user: User = Depends(get_current_user),
):
    """Обновить документ (статус, тип, этап, язык, приоритет и др.)."""
    doc = await service.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    doc = await service.update(doc_id, request, user_id=None)
    return doc


@router.delete(
    "/documents/{doc_id}",
    summary="Удалить документ",
)
async def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicDocumentService = Depends(_get_doc_service),
):
    """Удалить документ."""
    result = await service.delete(doc_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    return {"success": result}


@router.post(
    "/documents/{doc_id}/assign-to-me",
    response_model=DocumentResponse,
    summary="Назначить документ на себя",
)
async def assign_document_to_me(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicDocumentService = Depends(_get_doc_service),
):
    """Назначить документ на текущего пользователя."""
    try:
        return await service.assign_to_me(doc_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/documents/{doc_id}/assign-to-user",
    response_model=DocumentResponse,
    summary="Назначить документ на пользователя",
)
async def assign_document_to_user(
    doc_id: int,
    assignee_id: int,
    service: PublicDocumentService = Depends(_get_doc_service),
    current_user: User = Depends(get_current_user),
):
    """Назначить документ на указанного пользователя."""
    try:
        return await service.assign_to_user(doc_id, assignee_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/documents/{doc_id}/unassign",
    response_model=DocumentResponse,
    summary="Снять назначение документа",
)
async def unassign_document(
    doc_id: int,
    service: PublicDocumentService = Depends(_get_doc_service),
    current_user: User = Depends(get_current_user),
):
    """Снять назначение с документа."""
    try:
        return await service.unassign(doc_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# === Блокировка ===
@router.post("/documents/{doc_id}/lock", response_model=DocumentResponse, summary="Заблокировать документ")
async def lock_document(doc_id: int, current_user: User = Depends(get_current_user), service: PublicDocumentService = Depends(_get_doc_service)):
    try: return await service.lock(doc_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/documents/{doc_id}/unlock", response_model=DocumentResponse, summary="Разблокировать документ")
async def unlock_document(doc_id: int, current_user: User = Depends(get_current_user), service: PublicDocumentService = Depends(_get_doc_service)):
    try: return await service.unlock(doc_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# === Архив ===
@router.post("/documents/{doc_id}/archive", response_model=DocumentResponse, summary="Архивировать документ")
async def archive_document(doc_id: int, current_user: User = Depends(get_current_user), service: PublicDocumentService = Depends(_get_doc_service)):
    try: return await service.archive(doc_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/documents/{doc_id}/unarchive", response_model=DocumentResponse, summary="Разархивировать документ")
async def unarchive_document(doc_id: int, current_user: User = Depends(get_current_user), service: PublicDocumentService = Depends(_get_doc_service)):
    try: return await service.unarchive(doc_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# === Анонимизация ===
@router.post("/documents/{doc_id}/anonymize", response_model=DocumentResponse, summary="Анонимизировать документ")
async def anonymize_document(doc_id: int, current_user: User = Depends(get_current_user), service: PublicDocumentService = Depends(_get_doc_service)):
    try: return await service.anonymize(doc_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# === Статус ===
@router.post("/documents/{doc_id}/change-status", response_model=DocumentResponse, summary="Изменить статус")
async def change_document_status(doc_id: int, status: DocumentStatus, current_user: User = Depends(get_current_user), service: PublicDocumentService = Depends(_get_doc_service)):
    try: return await service.change_status(doc_id, status, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# === Приоритет ===
@router.post("/documents/{doc_id}/change-priority", response_model=DocumentResponse, summary="Изменить приоритет")
async def change_document_priority(doc_id: int, priority: DocumentPriority, current_user: User = Depends(get_current_user), service: PublicDocumentService = Depends(_get_doc_service)):
    try: return await service.change_priority(doc_id, priority, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# === Этап ===
@router.post("/documents/{doc_id}/change-stage", response_model=DocumentResponse, summary="Изменить этап")
async def change_document_stage(doc_id: int, stage: DocumentStage, current_user: User = Depends(get_current_user), service: PublicDocumentService = Depends(_get_doc_service)):
    try: return await service.change_stage(doc_id, stage, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# === Язык ===
@router.post("/documents/{doc_id}/change-language", response_model=DocumentResponse, summary="Изменить язык")
async def change_document_language(doc_id: int, language: DocumentLanguage, current_user: User = Depends(get_current_user), service: PublicDocumentService = Depends(_get_doc_service)):
    try: return await service.change_language(doc_id, language, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
