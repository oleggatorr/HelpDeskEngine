from pydantic import BaseModel, ConfigDict, field_validator, Field
from datetime import datetime
from typing import Optional, List

from app.reports.enums import DocumentStage, DocumentStatus, DocumentLanguage, DocumentPriority
from app.reports.correction.models import CorrectionStatus


class CorrectionCreate(BaseModel):
    """Схема создания корректирующего действия. Документ создаётся в сервисе автоматически."""
    title: str = Field(..., min_length=3, max_length=200, description="Краткое название")
    description: Optional[str] = Field(None, description="Описание отклонения/проблемы")
    corrective_action: str = Field(..., min_length=3, description="Фактически выполненные действия")
    
    status: CorrectionStatus = CorrectionStatus.PLANNED
    planned_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None  # ✅ Исправлена опечатка

    # Поля для авто-создания документа
    doc_status: DocumentStatus = DocumentStatus.OPEN
    doc_language: DocumentLanguage = DocumentLanguage.RU
    doc_priority: DocumentPriority = DocumentPriority.MEDIUM
    doc_assigned_to: Optional[int] = None

    attachment_files: Optional[List[dict]] = None  # [{"file_path": str, "file_type": str}]


class CorrectionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    corrective_action: Optional[str] = Field(None, min_length=3)
    status: Optional[CorrectionStatus] = None
    planned_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None


class CorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ✅ Обязательно для Pydantic v2 + SQLAlchemy

    id: int
    document_id: int
    problem_registration_id: int

    # Данные из JOIN с Document
    track_id: Optional[str] = None
    doc_created_at: Optional[datetime] = None
    doc_current_stage: Optional[str] = None
    doc_status: Optional[DocumentStatus] = None
    is_locked: bool = False
    is_archived: bool = False
    assigned_to: Optional[int] = None

    # Собственные поля
    title: str
    description: Optional[str] = None
    corrective_action: str
    status: CorrectionStatus
    planned_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    created_by: Optional[int] = None
    completed_by: Optional[int] = None
    verified_by: Optional[int] = None


class CorrectionListResponse(BaseModel):  # ✅ Исправлена опечатка
    model_config = ConfigDict(from_attributes=True)
    items: List[CorrectionResponse]
    total: int


class CorrectionFilter(BaseModel):
    # Фильтры по документу
    track_id: Optional[str] = None
    doc_created_from: Optional[datetime] = None
    doc_created_to: Optional[datetime] = None
    doc_status: Optional[DocumentStatus] = None
    doc_type_id: Optional[int] = None
    doc_current_stage: Optional[str] = None
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    is_locked: Optional[bool] = None

    # Фильтры по коррекции
    title: Optional[str] = None
    status: Optional[CorrectionStatus] = None
    planned_date_from: Optional[datetime] = None
    planned_date_to: Optional[datetime] = None

    # Пагинация и сортировка
    page: int = 1
    limit: int = 20
    sort_by: str = "id"
    sort_order: str = "desc"

    @field_validator("sort_order", mode="before")
    @classmethod
    def validate_sort_order(cls, v):
        if v and v.lower() not in ("asc", "desc"):
            return "desc"
        return v.lower() if v else "desc"