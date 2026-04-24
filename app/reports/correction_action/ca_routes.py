from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.reports.correction_action.ca_public_services import PublicCorrectionActionService
from app.reports.correction_action.ca_schemas import (
    CorrectionActionCreate,
    CorrectionActionUpdate,
    CorrectionActionResponse,
    CorrectionActionListResponse,
    CorrectionActionFilter,
)

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db)) -> PublicCorrectionActionService:
    return PublicCorrectionActionService(db)



@router.get(
    "/correction-actions",
    response_model=CorrectionActionListResponse,
    summary="Список корректирующих действий",
)
async def list_actions(
    filters: CorrectionActionFilter = Depends(),
    service: PublicCorrectionActionService = Depends(_get_service),
):
    return await service.get_all(filters)




# =========================================================
# CREATE
# =========================================================
@router.post(
    "/correction-actions",
    response_model=CorrectionActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать корректирующее действие",
)
async def create_action(
    request: CorrectionActionCreate,
    created_by: int,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    return await service.create(request, created_by)


# =========================================================
# READ
# =========================================================
@router.get(
    "/correction-actions/{action_id}",
    response_model=CorrectionActionResponse,
    summary="Получить действие по ID",
)
async def get_action(
    action_id: int,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    result = await service.get_by_id(action_id)
    if not result:
        raise HTTPException(status_code=404, detail="Действие не найдено")
    return result





@router.get(
    "/correction-actions/correction/{correction_id}",
    response_model=CorrectionActionListResponse,
    summary="Действия по коррекции",
)
async def get_by_correction(
    correction_id: int,
    filters: CorrectionActionFilter = Depends(),
    service: PublicCorrectionActionService = Depends(_get_service),
):
    return await service.get_by_correction_id(correction_id, filters)


@router.get(
    "/correction-actions/assigned/{user_id}",
    response_model=CorrectionActionListResponse,
    summary="Действия, назначенные пользователю",
)
async def get_assigned(
    user_id: int,
    filters: CorrectionActionFilter = Depends(),
    service: PublicCorrectionActionService = Depends(_get_service),
):
    return await service.get_assigned(user_id, filters)


# =========================================================
# UPDATE
# =========================================================
@router.put(
    "/correction-actions/{action_id}",
    response_model=CorrectionActionResponse,
    summary="Обновить корректирующее действие",
)
async def update_action(
    action_id: int,
    request: CorrectionActionUpdate,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    result = await service.update(action_id, request)
    if not result:
        raise HTTPException(status_code=404, detail="Действие не найдено")
    return result


# =========================================================
# STATUS ACTIONS
# =========================================================
@router.post(
    "/correction-actions/{action_id}/start",
    response_model=CorrectionActionResponse,
    summary="Начать выполнение действия",
)
async def start_action(
    action_id: int,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    result = await service.start_action(action_id)
    if not result:
        raise HTTPException(status_code=404, detail="Действие не найдено")
    return result


@router.post(
    "/correction-actions/{action_id}/complete",
    response_model=CorrectionActionResponse,
    summary="Завершить действие",
)
async def complete_action(
    action_id: int,
    comment: str | None = None,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    result = await service.complete_action(action_id, comment=comment)
    if not result:
        raise HTTPException(status_code=404, detail="Действие не найдено")
    return result


@router.post(
    "/correction-actions/{action_id}/skip",
    response_model=CorrectionActionResponse,
    summary="Пропустить действие",
)
async def skip_action(
    action_id: int,
    comment: str | None = None,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    result = await service.skip_action(action_id, comment=comment)
    if not result:
        raise HTTPException(status_code=404, detail="Действие не найдено")
    return result


# =========================================================
# ASSIGNMENT
# =========================================================
@router.post(
    "/correction-actions/{action_id}/assign",
    response_model=CorrectionActionResponse,
    summary="Назначить исполнителя",
)
async def assign_user(
    action_id: int,
    user_id: int,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    result = await service.assign_user(action_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Действие не найдено")
    return result


@router.post(
    "/correction-actions/{action_id}/assign-self",
    response_model=CorrectionActionResponse,
    summary="Назначить себя",
)
async def assign_self(
    action_id: int,
    user_id: int,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    result = await service.assign_self(action_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Действие не найдено")
    return result


@router.post(
    "/correction-actions/{action_id}/unassign",
    response_model=CorrectionActionResponse,
    summary="Снять назначение",
)
async def unassign(
    action_id: int,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    result = await service.unassign(action_id)
    if not result:
        raise HTTPException(status_code=404, detail="Действие не найдено")
    return result


# =========================================================
# DELETE
# =========================================================
@router.delete(
    "/correction-actions/{action_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить действие",
)
async def delete_action(
    action_id: int,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    deleted = await service.delete(action_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Действие не найдено")


# =========================================================
# BULK
# =========================================================
@router.post(
    "/correction-actions/correction/{correction_id}/close",
    summary="Закрыть все действия коррекции",
)
async def close_correction_actions(
    correction_id: int,
    service: PublicCorrectionActionService = Depends(_get_service),
):
    count = await service.close_correction_actions(correction_id)
    return {"closed": count}