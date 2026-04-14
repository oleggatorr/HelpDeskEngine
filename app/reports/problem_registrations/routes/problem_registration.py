from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.reports.problem_registrations.public_services.problem_registration import PublicProblemRegistrationService
from app.reports.problem_registrations.schemas.problem_registration import (
    ProblemRegistrationCreate,
    ProblemRegistrationUpdate,
    ProblemRegistrationResponse,
    ProblemRegistrationListResponse,
    ProblemRegistrationFilter,
)

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db)) -> PublicProblemRegistrationService:
    return PublicProblemRegistrationService(db)


@router.post(
    "/problem-registrations",
    response_model=ProblemRegistrationResponse,
    summary="Создать регистрацию проблемы",
    status_code=status.HTTP_201_CREATED,
)
async def create_problem_registration(
    request: ProblemRegistrationCreate,
    created_by: int,
    service: PublicProblemRegistrationService = Depends(_get_service),
):
    """
    Создать регистрацию проблемы.
    Документ создаётся автоматически, привязывается к регистрации.
    """
    return await service.create(request, created_by=created_by)


@router.get(
    "/problem-registrations/{registration_id}",
    response_model=ProblemRegistrationResponse,
    summary="Регистрация проблемы по ID",
)
async def get_problem_registration(
    registration_id: int,
    service: PublicProblemRegistrationService = Depends(_get_service),
):
    """Получить регистрацию проблемы по ID."""
    result = await service.get_by_id(registration_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Регистрация не найдена")
    return result


@router.get(
    "/problem-registrations/document/{doc_id}",
    response_model=ProblemRegistrationResponse,
    summary="Регистрация по ID документа",
)
async def get_by_document(
    doc_id: int,
    service: PublicProblemRegistrationService = Depends(_get_service),
):
    """Получить регистрацию проблемы по ID документа."""
    result = await service.get_by_document_id(doc_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Регистрация не найдена")
    return result


@router.get(
    "/problem-registrations/track/{track_id}",
    response_model=ProblemRegistrationResponse,
    summary="Регистрация по трек-номеру документа",
)
async def get_by_track(
    track_id: str,
    service: PublicProblemRegistrationService = Depends(_get_service),
):
    """Получить регистрацию проблемы по трек-номеру документа."""
    result = await service.get_by_track_id(track_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Регистрация не найдена")
    return result


@router.get(
    "/problem-registrations",
    response_model=ProblemRegistrationListResponse,
    summary="Список регистраций проблем",
)
async def list_problem_registrations(
    skip: int = 0,
    limit: int = 100,
    filters: ProblemRegistrationFilter = Depends(),
    service: PublicProblemRegistrationService = Depends(_get_service),
):
    """Пагинированный список всех регистраций проблем с фильтрами."""
    return await service.get_all(skip=skip, limit=limit, filters=filters)


@router.put(
    "/problem-registrations/{registration_id}",
    response_model=ProblemRegistrationResponse,
    summary="Обновить регистрацию проблемы",
)
async def update_problem_registration(
    registration_id: int,
    request: ProblemRegistrationUpdate,
    service: PublicProblemRegistrationService = Depends(_get_service),
):
    """Обновить регистрацию проблемы по ID."""
    result = await service.update(registration_id, request)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Регистрация не найдена")
    return result


@router.delete(
    "/problem-registrations/{registration_id}",
    summary="Удалить регистрацию проблемы",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_problem_registration(
    registration_id: int,
    service: PublicProblemRegistrationService = Depends(_get_service),
):
    """Удалить регистрацию проблемы по ID."""
    deleted = await service.delete(registration_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Регистрация не найдена")
