from typing import Optional, List, Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict, BeforeValidator, field_validator
from typing_extensions import Annotated

from app.reports.documents.document_models import (
    DocumentStatus, DocumentLanguage, DocumentPriority
)
from app.reports.models import ProblemAction

from app.reports.enums import *


# ========================
# UNIVERSAL ENUM PARSER (soft mode)
# ========================

def parse_enum_safe(enum_cls, value: Any, default=None):
    if value is None or value == "":
        return default

    if isinstance(value, enum_cls):
        return value

    # match by value
    for member in enum_cls:
        if member.value == value or str(member.value) == str(value):
            return member

    # match by name
    try:
        return enum_cls[str(value).upper()]
    except (KeyError, AttributeError):
        pass

    # fallback вместо ошибки (как было раньше)
    return default


# ========================
# REUSABLE VALIDATORS
# ========================

DocStatusValidator = Annotated[
    Optional[DocumentStatus],
    BeforeValidator(lambda v: parse_enum_safe(DocumentStatus, v, DocumentStatus.OPEN))
]

DocLanguageValidator = Annotated[
    Optional[DocumentLanguage],
    BeforeValidator(lambda v: parse_enum_safe(DocumentLanguage, v, DocumentLanguage.RU))
]

DocPriorityValidator = Annotated[
    Optional[DocumentPriority],
    BeforeValidator(lambda v: parse_enum_safe(DocumentPriority, v, DocumentPriority.MEDIUM))
]

ProblemActionValidator = Annotated[
    Optional[ProblemAction],
    BeforeValidator(lambda v: parse_enum_safe(ProblemAction, v, None))
]


# ========================
# CREATE
# ========================

class ProblemRegistrationCreate(BaseModel):
    """Создание регистрации проблемы (документ создаётся автоматически)."""
    model_config = ConfigDict(use_enum_values=True)

    # ProblemRegistration fields
    subject: Optional[str] = None
    detected_at: Optional[datetime] = None
    location_id: Optional[int] = None
    description: Optional[str] = None
    nomenclature: Optional[str] = None
    approved_at: Optional[datetime] = None
    action: ProblemActionValidator = None
    responsible_department_id: Optional[int] = None
    comment: Optional[str] = None

    # Document fields
    doc_status: DocStatusValidator = DocumentStatus.OPEN
    doc_language: DocLanguageValidator = DocumentLanguage.RU
    doc_priority: DocPriorityValidator = DocumentPriority.MEDIUM
    doc_assigned_to: Optional[int] = None

    # Attachments
    attachment_files: Optional[List[dict]] = None


# ========================
# UPDATE
# ========================

class ProblemRegistrationUpdate(BaseModel):
    """Обновление основной информации."""
    model_config = ConfigDict(use_enum_values=True)

    subject: Optional[str] = None
    detected_at: Optional[datetime] = None
    location_id: Optional[int] = None
    description: Optional[str] = None
    nomenclature: Optional[str] = None

    doc_assigned_to: Optional[int] = None


# ========================
# DETAIL UPDATE
# ========================

class ProblemRegistrationDetailUpdate(BaseModel):
    """Обновление доп. информации."""
    model_config = ConfigDict(use_enum_values=True)

    approved_at: Optional[datetime] = None
    action: ProblemActionValidator = ProblemAction.UNDEFINED
    responsible_department_id: Optional[int] = None
    comment: Optional[str] = None


# ========================
# RESPONSE
# ========================

class ProblemRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    document_id: int

    # Document (join)
    track_id: Optional[str] = None
    doc_created_at: Optional[datetime] = None
    doc_current_stage: Optional[str] = None
    doc_status: Optional[DocumentStatus] = None
    is_locked: bool = False
    is_archived: bool = False
    assigned_to: Optional[int] = None

    # ProblemRegistration
    subject: Optional[str] = None
    detected_at: Optional[datetime] = None
    location_id: Optional[int] = None
    description: Optional[str] = None
    nomenclature: Optional[str] = None

    approved_at: Optional[datetime] = None
    action: Optional[ProblemAction] = None
    responsible_department_id: Optional[int] = None
    comment: Optional[str] = None

    # Extra
    location_name: Optional[str] = None
    department_name: Optional[str] = None
    created_by: Optional[int] = None


# ========================
# LIST RESPONSE
# ========================

class ProblemRegistrationListResponse(BaseModel):
    items: List[ProblemRegistrationResponse]
    total: int


# ========================
# FILTER
# ========================

class ProblemRegistrationFilter(BaseModel):
    """Фильтры поиска."""
    model_config = ConfigDict(use_enum_values=True)

    # ProblemRegistration
    subject: Optional[str] = None
    detected_from: Optional[datetime] = None
    detected_to: Optional[datetime] = None
    location_id: Optional[int] = None
    description: Optional[str] = None
    nomenclature: Optional[str] = None
    approved_from: Optional[datetime] = None
    approved_to: Optional[datetime] = None
    action: ProblemActionValidator = None
    responsible_department_id: Optional[int] = None
    comment: Optional[str] = None

    # Document
    track_id: Optional[str] = None
    doc_created_from: Optional[datetime] = None
    doc_created_to: Optional[datetime] = None
    doc_status: DocStatusValidator = None
    doc_type_id: Optional[int] = None
    doc_current_stage: Optional[str] = None
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    is_locked: Optional[bool] = None

    # Sorting
    sort_by: Optional[str] = "id"
    sort_order: Optional[str] = "desc"

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        allowed = {
            "id", "subject", "detected_at",
            "doc_created_at", "doc_status"
        }
        if v not in allowed:
            raise ValueError(f"sort_by должен быть одним из: {', '.join(sorted(allowed))}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        if v and v.lower() not in ("asc", "desc"):
            raise ValueError("sort_order должен быть 'asc' или 'desc'")
        return v.lower() if v else v

    @field_validator("is_locked", mode="before")
    @classmethod
    def parse_bool(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "on")
        return bool(v)