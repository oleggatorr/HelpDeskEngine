from abc import ABC, abstractmethod
from typing import Optional
from app.reports.schemas import (
    CorrectiveActionCreate,
    CorrectiveActionResponse,
)


class ICorrectiveActionService(ABC):
    """
    Сервис корректирующих действий.
    Вход: CorrectiveActionCreate, ID.
    Выход: CorrectiveActionResponse.
    """

    @abstractmethod
    async def create(self, request: CorrectiveActionCreate) -> CorrectiveActionResponse:
        """Вход: CorrectiveActionCreate. Выход: CorrectiveActionResponse. Комментарий: создание Document + CorrectiveAction в одной транзакции."""
        ...

    @abstractmethod
    async def get_by_id(self, action_id: int) -> Optional[CorrectiveActionResponse]:
        """Вход: action_id. Выход: Optional[CorrectiveActionResponse]. Комментарий: получение действия по ID."""
        ...

    @abstractmethod
    async def get_by_document_id(self, doc_id: int) -> Optional[CorrectiveActionResponse]:
        """Вход: doc_id. Выход: Optional[CorrectiveActionResponse]. Комментарий: получение действия по ID документа."""
        ...
