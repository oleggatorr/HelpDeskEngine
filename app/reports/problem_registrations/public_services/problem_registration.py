from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.reports.problem_registrations.services.problem_registration_service import ProblemRegistrationService
from app.reports.documents.services.document_service import DocumentService
from app.reports.problem_registrations.schemas.problem_registration import (
    ProblemRegistrationCreate,
    ProblemRegistrationUpdate,
    ProblemRegistrationResponse,
    ProblemRegistrationListResponse,
)


class PublicProblemRegistrationService:
    """Публичный слой регистраций проблем."""

    def __init__(self, db: AsyncSession):
        doc_service = DocumentService(db)
        self._service = ProblemRegistrationService(db, doc_service)

    async def create(self, request: ProblemRegistrationCreate, created_by: int) -> ProblemRegistrationResponse:
        """Создать регистрацию проблемы. Документ создаётся автоматически."""
        return await self._service.create(request, created_by=created_by)

    async def get_by_id(self, registration_id: int) -> Optional[ProblemRegistrationResponse]:
        return await self._service.get_by_id(registration_id)

    async def get_by_document_id(self, doc_id: int) -> Optional[ProblemRegistrationResponse]:
        return await self._service.get_by_document_id(doc_id)

    async def get_by_track_id(self, track_id: str) -> Optional[ProblemRegistrationResponse]:
        """Получить регистрацию проблемы по трек-номеру документа."""
        return await self._service.get_by_track_id(track_id)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters=None,
    ) -> ProblemRegistrationListResponse:
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return ProblemRegistrationListResponse(items=result["items"], total=result["total"])

    async def update(self, registration_id: int, request: ProblemRegistrationUpdate) -> Optional[ProblemRegistrationResponse]:
        """Обновить регистрацию проблемы."""
        # Проверяем, заблокирован ли документ
        item = await self.get_by_id(registration_id)
        if item and item.is_locked:
            raise ValueError("Редактирование заблокированного документа невозможно")

        result = await self._service.update(registration_id, request)
        if not result:
            return None
        return result

    async def confirm(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Подтвердить регистрацию проблемы (заблокировать документ)."""
        item = await self.get_by_id(registration_id)
        if not item:
            return None
        if item.is_locked:
            return item  # Уже заблокирован

        from app.reports.documents.public_services.document import PublicDocumentService
        doc_service = PublicDocumentService(self._service.db)
        await doc_service.lock(item.document_id, user_id=user_id)

        # Возвращаем обновлённую регистрацию
        return await self.get_by_id(registration_id)

    async def unconfirm(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Снять блокировку регистрации проблемы (разблокировать документ)."""
        item = await self.get_by_id(registration_id)
        if not item:
            return None
        if not item.is_locked:
            return item  # Уже разблокирован

        from app.reports.documents.public_services.document import PublicDocumentService
        doc_service = PublicDocumentService(self._service.db)
        await doc_service.unlock(item.document_id, user_id=user_id)

        # Возвращаем обновлённую регистрацию
        return await self.get_by_id(registration_id)

    async def delete(self, registration_id: int) -> bool:
        """Удалить регистрацию проблемы."""
        return await self._service.delete(registration_id)

    async def get_my(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> ProblemRegistrationListResponse:
        """Получить список регистраций, созданных пользователем."""
        from app.reports.problem_registrations.schemas.problem_registration import ProblemRegistrationFilter
        filters = ProblemRegistrationFilter(
            created_by=user_id,
            sort_by="id",
            sort_order="desc",
        )
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return ProblemRegistrationListResponse(items=result["items"], total=result["total"])
