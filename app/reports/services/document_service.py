from abc import ABC, abstractmethod
from typing import Optional
from app.reports.schemas import (
    DocumentResponse,
    DocumentListResponse,
    DocType,
    DocStatus,
)


class IDocumentService(ABC):
    """
    Сервис документов.
    Вход: фильтры, ID.
    Выход: DocumentResponse, DocumentListResponse.
    """

    @abstractmethod
    async def get_by_id(self, doc_id: int) -> Optional[DocumentResponse]:
        """Вход: doc_id. Выход: Optional[DocumentResponse]. Комментарий: получение документа по ID."""
        ...

    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        doc_type: Optional[DocType] = None,
        status: Optional[DocStatus] = None,
        creator_id: Optional[int] = None,
    ) -> DocumentListResponse:
        """Вход: skip, limit, фильтры. Выход: DocumentListResponse. Комментарий: пагинированный список."""
        ...

    @abstractmethod
    async def update_status(self, doc_id: int, status: DocStatus) -> DocumentResponse:
        """Вход: doc_id, status. Выход: DocumentResponse. Комментарий: изменение статуса документа."""
        ...

    @abstractmethod
    async def delete(self, doc_id: int) -> bool:
        """Вход: doc_id. Выход: bool. Комментарий: удаление документа с каскадным удалением расширения."""
        ...
