from abc import ABC, abstractmethod
from typing import Optional
from app.reports.schemas import (
    NonconformityReportCreate,
    NonconformityReportResponse,
)


class INonconformityReportService(ABC):
    """
    Сервис отчетов о несоответствии.
    Вход: NonconformityReportCreate, ID.
    Выход: NonconformityReportResponse.
    """

    @abstractmethod
    async def create(self, request: NonconformityReportCreate) -> NonconformityReportResponse:
        """Вход: NonconformityReportCreate. Выход: NonconformityReportResponse. Комментарий: создание Document + NonconformityReport в одной транзакции."""
        ...

    @abstractmethod
    async def get_by_id(self, report_id: int) -> Optional[NonconformityReportResponse]:
        """Вход: report_id. Выход: Optional[NonconformityReportResponse]. Комментарий: получение отчета по ID."""
        ...

    @abstractmethod
    async def get_by_document_id(self, doc_id: int) -> Optional[NonconformityReportResponse]:
        """Вход: doc_id. Выход: Optional[NonconformityReportResponse]. Комментарий: получение отчета по ID документа."""
        ...
