# app\reports\correction\schemas\correction.py
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List

# Укажите актуальный путь к вашему Enum
from app.reports.correction.models import CorrectionStatus  


class CorrectionBase(BaseModel):
    """Базовые поля, общие для создания и чтения"""
    title: str = Field(..., min_length=3, max_length=200, description="Краткое название корректирующего действия")
    description: Optional[str] = Field(None, description="Описание отклонения/проблемы")
    corrective_action: str = Field(..., min_length=3, description="Фактически выполненные действия")
    status: CorrectionStatus = Field(default=CorrectionStatus.PLANNED, description="Текущий статус")
    planned_date: Optional[datetime] = Field(None, description="Плановый срок выполнения")
    completed_date: Optional[datetime] = Field(None, description="Фактическая дата выполнения")


class CorrectionCreate(CorrectionBase):
    """Схема для POST /corrections/"""
    document_id: int = Field(..., gt=0, description="ID родительского документа")
    problem_registration_id: int = Field(..., gt=0, description="ID заявки (ProblemRegistration)")
    # status по умолчанию PLANNED, но можно явно передать другой при создании


class CorrectionUpdate(BaseModel):
    """Схема для PATCH /corrections/{id} — только изменяемые поля"""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    corrective_action: Optional[str] = Field(None, min_length=3)
    status: Optional[CorrectionStatus] = None
    planned_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    
    # 🔒 Обычно FK не меняют после создания. Если нужно, раскомментируйте:
    # document_id: Optional[int] = Field(None, gt=0)
    # problem_registration_id: Optional[int] = Field(None, gt=0)


class CorrectionResponse(CorrectionBase):
    """Схема для ответа API — включает ID и технические поля"""
    model_config = ConfigDict(from_attributes=True)  # ✅ Pydantic v2
    
    id: int
    document_id: int
    problem_registration_id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    is_locked: bool 

class CorrectionFilter(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    title: Optional[str] = None
    status: Optional[CorrectionStatus] = None
    document_id: Optional[int] = None
    problem_registration_id: Optional[int] = None
    created_by: Optional[int] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    
    # Фильтры по родительскому документу
    doc_track_id: Optional[str] = None
    doc_status: Optional[str] = None  # или DocumentStatus
    
    # Пагинация и сортировка
    sort_by: Optional[str] = None      # "id", "title", "status", "created_at", "track_id"
    sort_order: Optional[str] = None   # "asc", "desc"

class CorrectionListResponse(BaseModel):
    """Схема списка регистраций проблем с пагинацией."""
    items: List[CorrectionResponse]
    total: int