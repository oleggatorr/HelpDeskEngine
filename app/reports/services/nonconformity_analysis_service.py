from abc import ABC, abstractmethod
from typing import Optional
from app.reports.schemas import (
    NonconformityAnalysisCreate,
    NonconformityAnalysisResponse,
)


class INonconformityAnalysisService(ABC):
    """
    Сервис анализа несоответствий.
    Вход: NonconformityAnalysisCreate, ID.
    Выход: NonconformityAnalysisResponse.
    """

    @abstractmethod
    async def create(self, request: NonconformityAnalysisCreate) -> NonconformityAnalysisResponse:
        """Вход: NonconformityAnalysisCreate. Выход: NonconformityAnalysisResponse. Комментарий: создание Document + NonconformityAnalysis в одной транзакции."""
        ...

    @abstractmethod
    async def get_by_id(self, analysis_id: int) -> Optional[NonconformityAnalysisResponse]:
        """Вход: analysis_id. Выход: Optional[NonconformityAnalysisResponse]. Комментарий: получение анализа по ID."""
        ...

    @abstractmethod
    async def get_by_document_id(self, doc_id: int) -> Optional[NonconformityAnalysisResponse]:
        """Вход: doc_id. Выход: Optional[NonconformityAnalysisResponse]. Комментарий: получение анализа по ID документа."""
        ...
