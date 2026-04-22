# app/reports/correction/routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.reports.correction.correction_public_services import PublicCorrectionService
from app.reports.correction.schemas.correction import (
    CorrectionCreate,
    CorrectionUpdate,
    CorrectionResponse,
    CorrectionListResponse,
    CorrectionFilter,
    CorrectionStatus,
)

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db)) -> PublicCorrectionService:
    return PublicCorrectionService(db)


# ==========================================
# 🆕 CREATE & READ
# ==========================================
@router.post(
    "/",
    response_model=CorrectionResponse,
    summary="Создать корректирующее действие",
    status_code=status.HTTP_201_CREATED,
)
async def create_correction(
    request: CorrectionCreate,
    created_by: int = Query(..., description="ID пользователя-создателя"),
    service: PublicCorrectionService = Depends(_get_service),
):
    print(*request, sep = '\n')
    """Создать коррекцию. Документ и чат создаются автоматически."""
    return await service.create(request, created_by=created_by)


@router.get(
    "/{correction_id}",
    response_model=CorrectionResponse,
    summary="Коррекция по ID",
)
async def get_correction(
    correction_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.get_by_id(correction_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.get(
    "/document/{doc_id}",
    response_model=CorrectionResponse,
    summary="Коррекция по ID документа",
)
async def get_by_document(
    doc_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.get_by_document_id(doc_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.get(
    "/track/{track_id}",
    response_model=CorrectionResponse,
    summary="Коррекция по трек-номеру",
)
async def get_by_track(
    track_id: str,
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.get_by_track_id(track_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.get(
    "/by-pr/{pr_id}",
    response_model=CorrectionResponse,
    summary="Коррекция по ID заявки",
)
async def get_by_problem_registration(
    pr_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.get_by_problem_registration_id(pr_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


# ==========================================
# 📊 LIST & FILTER
# ==========================================
@router.get(
    "/",
    response_model=CorrectionListResponse,
    summary="Список коррекций с фильтрацией",
)
async def list_corrections(
    skip: int = Query(0, ge=0, description="Смещение (пагинация)"),
    limit: int = Query(20, ge=1, le=100, description="Лимит записей"),
    filters: CorrectionFilter = Depends(),
    service: PublicCorrectionService = Depends(_get_service),
):
    """Пагинированный список всех корректирующих действий."""
    return await service.get_all(skip=skip, limit=limit, filters=filters)


@router.get(
    "/my",
    response_model=CorrectionListResponse,
    summary="Мои коррекции",
)
async def get_my_corrections(
    user_id: int = Query(..., description="ID пользователя"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: PublicCorrectionService = Depends(_get_service),
):
    return await service.get_my(user_id=user_id, skip=skip, limit=limit)


@router.get(
    "/assigned",
    response_model=CorrectionListResponse,
    summary="Коррекции, назначенные на меня",
)
async def get_assigned_corrections(
    user_id: int = Query(..., description="ID пользователя"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: PublicCorrectionService = Depends(_get_service),
):
    return await service.get_assigned(user_id=user_id, skip=skip, limit=limit)


# ==========================================
# ✏️ UPDATE & DELETE
# ==========================================
@router.put(
    "/{correction_id}",
    response_model=CorrectionResponse,
    summary="Обновить коррекцию",
)
async def update_correction(
    correction_id: int,
    request: CorrectionUpdate,
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.update(correction_id, request)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.delete(
    "/{correction_id}",
    summary="Удалить коррекцию (soft-delete)",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_correction(
    correction_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    deleted = await service.delete(correction_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена или уже удалена")


# ==========================================
# 🔒 LIFECYCLE (LOCK/ARCHIVE)
# ==========================================
@router.post(
    "/{correction_id}/confirm",
    response_model=CorrectionResponse,
    summary="Подтвердить и заблокировать коррекцию",
)
async def confirm_correction(
    correction_id: int,
    user_id: int = Query(..., description="ID подтверждающего пользователя"),
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.confirm(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/{correction_id}/unconfirm",
    response_model=CorrectionResponse,
    summary="Снять блокировку (вернуть на редактирование)",
)
async def unconfirm_correction(
    correction_id: int,
    user_id: int = Query(..., description="ID пользователя"),
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.unconfirm(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/{correction_id}/archive",
    response_model=CorrectionResponse,
    summary="Архивировать коррекцию",
)
async def archive_correction(
    correction_id: int,
    user_id: int = Query(..., description="ID пользователя"),
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.archive(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/{correction_id}/unarchive",
    response_model=CorrectionResponse,
    summary="Восстановить коррекцию из архива",
)
async def unarchive_correction(
    correction_id: int,
    user_id: int = Query(..., description="ID пользователя"),
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.unarchive(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


# ==========================================
# 👤 ASSIGNMENT
# ==========================================
@router.post(
    "/{correction_id}/assign",
    response_model=CorrectionResponse,
    summary="Назначить пользователя",
)
async def assign_user_to_correction(
    correction_id: int,
    user_id_to_assign: int = Query(..., description="ID назначаемого пользователя"),
    current_user_id: int = Query(..., description="ID текущего пользователя (кто назначает)"),
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.assign_user(correction_id, user_id_to_assign=user_id_to_assign, current_user_id=current_user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/{correction_id}/assign-self",
    response_model=CorrectionResponse,
    summary="Назначить себя",
)
async def assign_self_to_correction(
    correction_id: int,
    user_id: int = Query(..., description="ID пользователя"),
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.assign_self(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/{correction_id}/unassign",
    response_model=CorrectionResponse,
    summary="Снять назначение",
)
async def unassign_correction(
    correction_id: int,
    current_user_id: int = Query(..., description="ID текущего пользователя"),
    service: PublicCorrectionService = Depends(_get_service),
):
    """✅ Исправлено: передан current_user_id, возвращён response"""
    result = await service.unassign(correction_id, current_user_id=current_user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


# ==========================================
# 🔄 STATUS WORKFLOW
# ==========================================
@router.put(
    "/{correction_id}/status",
    response_model=CorrectionResponse,
    summary="Изменить статус коррекции",
)
async def change_correction_status(
    correction_id: int,
    new_status: CorrectionStatus = Query(..., description="Новый статус (planned, in_progress, completed, verified, rejected)"),
    user_id: int = Query(..., description="ID пользователя, изменившего статус"),
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.change_status(correction_id, new_status=new_status, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/{correction_id}/close",
    response_model=CorrectionResponse,
    summary="Закрыть и верифицировать коррекцию",
)
async def close_correction(
    correction_id: int,
    user_id: int = Query(..., description="ID закрывающего пользователя"),
    service: PublicCorrectionService = Depends(_get_service),
):
    result = await service.close(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result