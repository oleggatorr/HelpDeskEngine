# app\reports\correction\schemas\correction.py
from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime
from typing import Optional, List

from app.reports.enums import DocumentStage, DocumentStatus, DocumentLanguage, DocumentPriority

# Укажите актуальный путь к вашему Enum
from app.reports.correction.models import CorrectionStatus  


class CorrectionCreate(BaseModel):
    """Схема создания регистрации проблемы (документ создаётся автоматически)."""
    # title: str = Field(..., min_length=3, max_length=200, description="Краткое название корректирующего действия")
    # description: Optional[str] = Field(None, description="Описание отклонения/проблемы")
    # corrective_action: str = Field(..., min_length=3, description="Фактически выполненные действия")
    # status: CorrectionStatus = Field(default=CorrectionStatus.PLANNED, description="Текущий статус")
    # planned_date: Optional[datetime] = Field(None, description="Плановый срок выполнения")
    # completed_date: Optional[datetime] = Field(None, description="Фактическая дата выполнения")

    subject: Optional[str] = None
    description: Optional[str] =  None
    status: Optional[CorrectionStatus] = CorrectionStatus.PLANNED
    planned_date: Optional[datetime] = None
    complited_date: Optional[datetime] = None

        # Поля Document (создаётся автоматически)
    doc_status: Optional[DocumentStatus] = DocumentStatus.OPEN
    doc_language: Optional[DocumentLanguage] = DocumentLanguage.RU
    doc_priority: Optional[DocumentPriority] = DocumentPriority.MEDIUM
    doc_assigned_to: Optional[int] = None

    # Вложения
    attachment_files: Optional[List[dict]] = None  # [{"file_path": str, "file_type": str}]

    @field_validator("doc_status", mode="before")
    @classmethod
    def parse_doc_status(cls, v):
        if v is None or v == "":
            return DocumentStatus.OPEN
        if isinstance(v, DocumentStatus):
            return v
        if isinstance(v, str):
            try:
                return DocumentStatus(v)
            except ValueError:
                return DocumentStatus.OPEN
        return v

    @field_validator("doc_language", mode="before")
    @classmethod
    def parse_doc_language(cls, v):
        if v is None or v == "":
            return DocumentLanguage.RU
        if isinstance(v, DocumentLanguage):
            return v
        if isinstance(v, str):
            try:
                return DocumentLanguage(v)
            except ValueError:
                return DocumentLanguage.RU
        return v

    @field_validator("doc_priority", mode="before")
    @classmethod
    def parse_doc_priority(cls, v):
        if v is None or v == "":
            return DocumentPriority.MEDIUM
        if isinstance(v, DocumentPriority):
            return v
        if isinstance(v, str):
            try:
                return DocumentPriority(v)
            except ValueError:
                return DocumentPriority.MEDIUM
        return v
    
    @field_validator("status", mode="before")
    @classmethod
    def parse_action(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, CorrectionStatus):
            return v.value  # Возвращаем строку 'CLOSED'
        if isinstance(v, str):
            try:
                # Валидируем, что строка допустима, но возвращаем её же
                CorrectionStatus(v)
                return v
            except ValueError:
                return None
        return v


class CorrectionUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] =  None
    status: Optional[CorrectionStatus] = None
    planned_date: Optional[datetime] = None
    complited_date: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def parse_action(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, CorrectionStatus):
            return v.value  # Возвращаем строку 'CLOSED'
        if isinstance(v, str):
            try:
                # Валидируем, что строка допустима, но возвращаем её же
                CorrectionStatus(v)
                return v
            except ValueError:
                return None
        return v



class CorrectionResponse(BaseModel):
    id: int
    document_id: int
    # Поля из документа (join)
    track_id: Optional[str] = None
    doc_created_at: Optional[datetime] = None
    doc_current_stage: Optional[str] = None
    doc_status: Optional[DocumentStatus] = None
    is_locked: bool = False
    is_archived: bool = False
    assigned_to: Optional[int] = None
    # Собственные поля
    subject: Optional[str] = None
    description: Optional[str] =  None
    status: Optional[CorrectionStatus] = None
    planned_date: Optional[datetime] = None
    complited_date: Optional[datetime] = None





class CorrectionListResponce(BaseModel):
    """"""
    items: List[CorrectionResponse]
    total: int


class CorrectionFilter(BaseModel):
    ''''''
    # Поля документов 
    track_id: Optional[str] = None
    doc_created_from: Optional[datetime] = None
    doc_created_to: Optional[datetime] = None
    doc_status: Optional[DocumentStatus] = None
    doc_type_id: Optional[int] = None
    doc_current_stage: Optional[str] = None
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    is_locked: Optional[bool] = None
    # Поля коррекции
    subject: Optional[str] = None
    description: Optional[str] =  None
    status: Optional[CorrectionStatus] = None
    planned_date: Optional[datetime] = None
    # Пагинация и сортировка
    sort_by: Optional[str] = "id"
    sort_order: Optional[str] = "desc"

    @field_validator("doc_status", "action", mode="before")
    @classmethod
    def parse_filter_enums(cls, v):
        if isinstance(v, str):
            return v
        if hasattr(v, 'value'):
            return v.value
        return v
    
    @field_validator("is_locked", mode="before")
    @classmethod
    def parse_bool_filter(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "on")
        return bool(v)

    
# class CorrectionCreate(CorrectionBase):
#     """Схема для POST /corrections/"""
#     document_id: int = Field(..., gt=0, description="ID родительского документа")
#     problem_registration_id: int = Field(..., gt=0, description="ID заявки (ProblemRegistration)")
#     # status по умолчанию PLANNED, но можно явно передать другой при создании


# class CorrectionUpdate(BaseModel):
#     """Схема для PATCH /corrections/{id} — только изменяемые поля"""
#     title: Optional[str] = Field(None, min_length=3, max_length=200)
#     description: Optional[str] = None
#     corrective_action: Optional[str] = Field(None, min_length=3)
#     status: Optional[CorrectionStatus] = None
#     planned_date: Optional[datetime] = None
#     completed_date: Optional[datetime] = None
    
#     # 🔒 Обычно FK не меняют после создания. Если нужно, раскомментируйте:
#     # document_id: Optional[int] = Field(None, gt=0)
#     # problem_registration_id: Optional[int] = Field(None, gt=0)


# class CorrectionResponse(CorrectionBase):
#     """Схема для ответа API — включает ID и технические поля"""
#     model_config = ConfigDict(from_attributes=True)  # ✅ Pydantic v2
    
#     id: int
#     document_id: int
#     problem_registration_id: int
#     created_at: datetime
#     updated_at: datetime
#     is_deleted: bool
#     is_locked: bool 

# class CorrectionFilter(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
    
#     title: Optional[str] = None
#     status: Optional[CorrectionStatus] = None
#     document_id: Optional[int] = None
#     problem_registration_id: Optional[int] = None
#     created_by: Optional[int] = None
#     created_from: Optional[datetime] = None
#     created_to: Optional[datetime] = None
    
#     # Фильтры по родительскому документу
#     doc_track_id: Optional[str] = None
#     doc_status: Optional[str] = None  # или DocumentStatus
    
#     # Пагинация и сортировка
#     sort_by: Optional[str] = None      # "id", "title", "status", "created_at", "track_id"
#     sort_order: Optional[str] = None   # "asc", "desc"

# class CorrectionListResponse(BaseModel):
#     """Схема списка регистраций проблем с пагинацией."""
#     items: List[CorrectionResponse]
#     total: int