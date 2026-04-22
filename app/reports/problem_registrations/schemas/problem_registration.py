from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict

from app.reports.enums import DocumentStage, DocumentStatus, DocumentLanguage, DocumentPriority

from app.reports.models import ProblemAction

class ProblemRegistrationCreate(BaseModel):
    """Схема создания регистрации проблемы (документ создаётся автоматически)."""
    # Поля ProblemRegistration
    subject: Optional[str] = None
    detected_at: Optional[datetime] = None
    location_id: Optional[int] = None
    description: Optional[str] = None
    nomenclature: Optional[str] = None
    approved_at: Optional[datetime] = None
    action: Optional[ProblemAction] = None
    responsible_department_id: Optional[int] = None
    comment: Optional[str] = None
    
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

    # @field_validator("action", mode="before")
    # @classmethod
    # def parse_action(cls, v):
    #     if v is None or v == "":
    #         return None
    #     if isinstance(v, ProblemAction):
    #         return v
    #     if isinstance(v, str):
    #         try:
    #             return ProblemAction(v)
    #         except ValueError:
    #             return None
    #     return v

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


class ProblemRegistrationUpdate(BaseModel):
    """Схема обновления регистрации проблемы."""
    subject: Optional[str] = None
    detected_at: Optional[datetime] = None
    location_id: Optional[int] = None
    description: Optional[str] = None
    nomenclature: Optional[str] = None
    # approved_at: Optional[datetime] = None
    # action: Optional[ProblemAction] = None
    # responsible_department_id: Optional[int] = None
    # comment: Optional[str] = None
    doc_assigned_to: Optional[int] = None

    # @field_validator("action", mode="before")
    # @classmethod
    # def parse_action(cls, v):
    #     if v is None or v == "":
    #         return None
    #     if isinstance(v, ProblemAction):
    #         return v
    #     if isinstance(v, str):
    #         try:
    #             return ProblemAction(v)
    #         except ValueError:
    #             return None
    #     return v


class ProblemRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
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
    detected_at: Optional[datetime] = None
    location_id: Optional[int] = None
    description: Optional[str] = None
    nomenclature: Optional[str] = None
    
    approved_at: Optional[datetime] = None
    action: Optional[ProblemAction] = None
    responsible_department_id: Optional[int] = None
    comment: Optional[str] = None

    location_name: Optional[str] = None
    department_name: Optional[str] = None
    created_by: Optional[int] = None  # если ещё не объявлено

    model_config = ConfigDict(from_attributes=True)  # убедитесь, что есть

    @field_validator("doc_status", "action", mode="before")
    @classmethod
    def parse_db_values(cls, v, info):
        if isinstance(v, str):
            return v
        if hasattr(v, 'value'):
            return v.value
        return v


class ProblemRegistrationListResponse(BaseModel):
    """Схема списка регистраций проблем с пагинацией."""
    items: List[ProblemRegistrationResponse]
    total: int


class ProblemRegistrationFilter(BaseModel):
    """Фильтры для поиска регистраций проблем (включая поля документа)."""
    # Поля ProblemRegistration
    subject: Optional[str] = None
    detected_from: Optional[datetime] = None
    detected_to: Optional[datetime] = None
    location_id: Optional[int] = None
    description: Optional[str] = None
    nomenclature: Optional[str] = None
    approved_from: Optional[datetime] = None
    approved_to: Optional[datetime] = None
    action: Optional[ProblemAction] = None
    responsible_department_id: Optional[int] = None
    comment: Optional[str] = None
    
    # Поля Document (через join)
    track_id: Optional[str] = None
    doc_created_from: Optional[datetime] = None
    doc_created_to: Optional[datetime] = None
    doc_status: Optional[DocumentStatus] = None
    doc_type_id: Optional[int] = None
    doc_current_stage: Optional[str] = None
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    is_locked: Optional[bool] = None
    
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



class ProblemRegistration_DetaleUpdate(BaseModel):
    """Схема обновления доп информации о регистрации проблемы."""
    approved_at: Optional[datetime] = None
    action: Optional[str] = ProblemAction.UNDEFINED.value 
    responsible_department_id: Optional[int] = None
    comment: Optional[str] = None

    @field_validator("action", mode="before")
    @classmethod
    def parse_action(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, ProblemAction):
            return v.value  # Возвращаем строку 'CLOSED'
        if isinstance(v, str):
            try:
                # Валидируем, что строка допустима, но возвращаем её же
                ProblemAction(v)
                return v
            except ValueError:
                return None
        return v