from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.reports.correction.correction_public_services import PublicCorrectionService
from app.reports.correction.schemas.correction import (
    CorrectionCreate,
    CorrectionUpdate,
    CorrectionResponse,
    CorrectionListResponse,
    CorrectionFilter,
)

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db)) -> PublicCorrectionService:
    """Dependency для получения сервиса коррекций."""
    return PublicCorrectionService(db)


# ------------------------------------------------------------------
# 🔹 CRUD
# ------------------------------------------------------------------

@router.post(
    "/corrections",
    response_model=CorrectionResponse,
    summary="Создать корректирующее действие",
    status_code=status.HTTP_201_CREATED,
)
async def create_correction(
    request: CorrectionCreate,
    created_by: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Создать корректирующее действие. Документ должен существовать."""
    return await service.create(request, created_by=created_by)


@router.get(
    "/corrections/{correction_id}",
    response_model=CorrectionResponse,
    summary="Коррекция по ID",
)
async def get_correction(
    correction_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Получить корректирующее действие по ID."""
    result = await service.get_by_id(correction_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.get(
    "/corrections/document/{doc_id}",
    response_model=List[CorrectionResponse],
    summary="Список коррекций по ID документа",
)
async def get_corrections_by_document(
    doc_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Получить все активные коррекции, привязанные к документу."""
    return await service.get_by_document_id(doc_id)


@router.get(
    "/corrections",
    response_model=CorrectionListResponse,
    summary="Список всех корректирующих действий",
)
async def list_corrections(
    skip: int = 0,
    limit: int = 100,
    filters: CorrectionFilter = Depends(),
    service: PublicCorrectionService = Depends(_get_service),
):
    """Пагинированный список всех коррекций с фильтрами и сортировкой."""
    return await service.get_all(skip=skip, limit=limit, filters=filters)


@router.patch(
    "/corrections/{correction_id}",
    response_model=CorrectionResponse,
    summary="Обновить корректирующее действие",
)
async def update_correction(
    correction_id: int,
    request: CorrectionUpdate,
    current_user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Частичное обновление коррекции. Блокирует изменение, если документ залочен."""
    result = await service.update(correction_id, request, current_user_id=current_user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.delete(
    "/corrections/{correction_id}",
    summary="Удалить корректирующее действие",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_correction(
    correction_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Soft-delete корректирующего действия."""
    deleted = await service.delete(correction_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")


# ------------------------------------------------------------------
# 🔄 Статусные переходы
# ------------------------------------------------------------------
@router.post(
    "/corrections/{correction_id}/start",
    response_model=CorrectionResponse,
    summary="Начать выполнение коррекции",
)
async def start_correction(
    correction_id: int,
    user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """PLANNED → IN_PROGRESS"""
    result = await service.start_execution(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена или заблокирована")
    return result


@router.post(
    "/corrections/{correction_id}/complete",
    response_model=CorrectionResponse,
    summary="Завершить выполнение коррекции",
)
async def complete_correction(
    correction_id: int,
    user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """IN_PROGRESS → COMPLETED (авто-фиксация даты и исполнителя)"""
    result = await service.complete_execution(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена или заблокирована")
    return result


@router.post(
    "/corrections/{correction_id}/verify",
    response_model=CorrectionResponse,
    summary="Верифицировать коррекцию",
)
async def verify_correction(
    correction_id: int,
    verifier_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """COMPLETED → VERIFIED"""
    result = await service.verify(correction_id, verifier_id=verifier_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/corrections/{correction_id}/reject",
    response_model=CorrectionResponse,
    summary="Отклонить/сбросить коррекцию",
)
async def reject_correction(
    correction_id: int,
    user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """IN_PROGRESS/COMPLETED → REJECTED или PLANNED"""
    result = await service.reject(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


# ------------------------------------------------------------------
# 🔒 Блокировка / Архив
# ------------------------------------------------------------------
@router.post(
    "/corrections/{correction_id}/confirm",
    response_model=CorrectionResponse,
    summary="Подтвердить и заблокировать коррекцию",
)
async def confirm_correction(
    correction_id: int,
    user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Заблокировать коррекцию и родительский документ."""
    result = await service.confirm(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/corrections/{correction_id}/unconfirm",
    response_model=CorrectionResponse,
    summary="Разблокировать коррекцию",
)
async def unconfirm_correction(
    correction_id: int,
    user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Разблокировать для редактирования."""
    result = await service.unconfirm(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/corrections/{correction_id}/archive",
    response_model=CorrectionResponse,
    summary="Архивировать коррекцию",
)
async def archive_correction(
    correction_id: int,
    user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Архивировать вместе с документом."""
    result = await service.archive(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/corrections/{correction_id}/unarchive",
    response_model=CorrectionResponse,
    summary="Восстановить коррекцию из архива",
)
async def unarchive_correction(
    correction_id: int,
    user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Восстановить из архива."""
    result = await service.unarchive(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


# ------------------------------------------------------------------
# 👤 Назначения
# ------------------------------------------------------------------
@router.post(
    "/corrections/{correction_id}/assign",
    response_model=CorrectionResponse,
    summary="Назначить пользователя на коррекцию",
)
async def assign_user_to_correction(
    correction_id: int,
    user_id_to_assign: int,
    current_user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Назначить исполнителя на коррекцию/документ."""
    result = await service.assign_user(correction_id, user_id_to_assign=user_id_to_assign, current_user_id=current_user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/corrections/{correction_id}/assign-self",
    response_model=CorrectionResponse,
    summary="Назначить себя на коррекцию",
)
async def assign_self_to_correction(
    correction_id: int,
    user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Назначить себя на выполнение."""
    result = await service.assign_self(correction_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


@router.post(
    "/corrections/{correction_id}/unassign",
    response_model=CorrectionResponse,
    summary="Снять назначение с коррекции",
)
async def unassign_correction(
    correction_id: int,
    current_user_id: int,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Снять назначение исполнителя."""
    result = await service.unassign(correction_id, current_user_id=current_user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коррекция не найдена")
    return result


# ------------------------------------------------------------------
# 📋 Персональные списки
# ------------------------------------------------------------------
@router.get(
    "/corrections/my",
    response_model=CorrectionListResponse,
    summary="Мои созданные коррекции",
)
async def get_my_corrections(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Коррекции, созданные текущим пользователем."""
    return await service.get_my(user_id=user_id, skip=skip, limit=limit)


@router.get(
    "/corrections/assigned",
    response_model=CorrectionListResponse,
    summary="Коррекции, назначенные на меня",
)
async def get_assigned_corrections(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    service: PublicCorrectionService = Depends(_get_service),
):
    """Коррекции, назначенные на пользователя (через документ)."""
    return await service.get_assigned(user_id=user_id, skip=skip, limit=limit)