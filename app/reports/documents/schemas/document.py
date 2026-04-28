from typing import Optional, List, Union, Any
from datetime import datetime
import re
import random
import string

from pydantic import BaseModel, field_validator, ConfigDict, BeforeValidator
from typing_extensions import Annotated
from app.reports.documents.document_models import DocumentStage, DocumentLanguage, DocumentPriority, DocumentStatus

from app.reports.enums import *
# from app.reports.enums import (
#     DocumentStage,      # IntEnum: NEW=1, IN_PROGRESS=2...
#     DocumentLanguage,   # str-enum: RU="ru", EN="en"
#     DocumentPriority,   # str-enum: LOW="low", HIGH="high"
#     DocumentStatus,     # str-enum: OPEN="open", CLOSED="closed"
# )

# ========================
# TRACK ID
# ========================

TRACK_ID_PATTERN = re.compile(r"^[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{4}$")


def generate_track_id() -> str:
    chars = string.ascii_uppercase + string.digits
    return f"{_rand(3)}-{_rand(3)}-{_rand(4)}"


def _rand(n: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


# ========================
# ENUM PARSER (универсальный, работает со str и int)
# ========================

def parse_enum_safe(enum_cls, value: Any):
    """
    Парсит значение в enum, поддерживая:
    - уже готовый экземпляр enum
    - строку/число, совпадающее с .value энума
    - строку, совпадающую с .name энума (для обратной совместимости)
    """
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    
    # Пробуем найти по значению (основной случай для БД)
    for member in enum_cls:
        if member.value == value or str(member.value) == str(value):
            return member
    
    # Пробуем найти по имени (для обратной совместимости с старым API)
    try:
        return enum_cls[value.upper()]
    except (KeyError, AttributeError):
        pass
    
    raise ValueError(f"Invalid value '{value}' for {enum_cls.__name__}. "
                     f"Valid values: {[m.value for m in enum_cls]}")


# Создаём переиспользуемые валидаторы
StageValidator = Annotated[Optional[DocumentStage], BeforeValidator(lambda v: parse_enum_safe(DocumentStage, v))]
StatusValidator = Annotated[Optional[DocumentStatus], BeforeValidator(lambda v: parse_enum_safe(DocumentStatus, v))]
LanguageValidator = Annotated[Optional[DocumentLanguage], BeforeValidator(lambda v: parse_enum_safe(DocumentLanguage, v))]
PriorityValidator = Annotated[Optional[DocumentPriority], BeforeValidator(lambda v: parse_enum_safe(DocumentPriority, v))]


# ========================
# CREATE
# ========================

class DocumentCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)  # ✅ В JSON уйдут .value, а не объекты

    track_id: Optional[str] = None
    status: DocumentStatus = DocumentStatus.OPEN
    doc_type_id: Optional[int] = None
    current_stage: DocumentStage = DocumentStage.NEW
    is_locked: bool = False
    is_archived: bool = False
    is_anonymized: bool = False
    language: DocumentLanguage = DocumentLanguage.RU
    priority: DocumentPriority = DocumentPriority.MEDIUM
    assigned_to: Optional[int] = None
    created_by: Optional[int] = 0
    attachment_files: Optional[List[dict]] = None

    @field_validator("track_id")
    @classmethod
    def validate_track_id(cls, v):
        if v and not TRACK_ID_PATTERN.match(v):
            raise ValueError("track_id должен быть в формате XXX-XXX-XXXX")
        return v

    # Применяем универсальные валидаторы
    current_stage: StageValidator
    status: StatusValidator
    language: LanguageValidator
    priority: PriorityValidator


# ========================
# UPDATE
# ========================

class DocumentUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    status: Optional[DocumentStatus] = None
    doc_type_id: Optional[int] = None
    current_stage: Optional[DocumentStage] = None
    is_locked: Optional[bool] = None
    is_archived: Optional[bool] = None
    is_anonymized: Optional[bool] = None
    language: Optional[DocumentLanguage] = None
    priority: Optional[DocumentPriority] = None
    assigned_to: Optional[int] = None

    current_stage: StageValidator
    status: StatusValidator
    language: LanguageValidator
    priority: PriorityValidator


# ========================
# RESPONSE
# ========================

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)  # ✅ Автоматическая сериализация .value

    id: int
    track_id: str
    created_at: datetime
    created_by: Optional[int] = None
    status: DocumentStatus          # ✅ Pydantic сам превратит в "open"/"closed"
    doc_type_id: Optional[int] = None
    current_stage: DocumentStage    # ✅ Pydantic сам превратит в 1/2/3/4
    is_locked: bool
    is_archived: bool
    is_anonymized: bool
    language: DocumentLanguage      # ✅ "ru"/"en"
    priority: DocumentPriority      # ✅ "low"/"high"
    assigned_to: Optional[int] = None

    # ❌ УДАЛИТЬ старый валидатор enum_to_str — он больше не нужен!
    # Благодаря use_enum_values=True Pydantic сам вернёт .value


# ========================
# LIST RESPONSE
# ========================

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


# ========================
# FILTER
# ========================

class DocumentFilter(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    track_id: Optional[str] = None
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    status: Optional[DocumentStatus] = None
    doc_type_id: Optional[int] = None
    current_stage: Optional[DocumentStage] = None
    is_locked: Optional[bool] = None
    is_archived: Optional[bool] = None
    is_anonymized: Optional[bool] = None
    language: Optional[DocumentLanguage] = None
    priority: Optional[DocumentPriority] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    sort_by: Optional[str] = "id"
    sort_order: Optional[str] = "desc"

    current_stage: StageValidator
    status: StatusValidator
    language: LanguageValidator
    priority: PriorityValidator

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        allowed = {"id", "track_id", "created_at", "created_by", "current_stage", "priority", "language"}
        if v not in allowed:
            raise ValueError(f"sort_by должен быть одним из: {', '.join(sorted(allowed))}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        if v and v.lower() not in ("asc", "desc"):
            raise ValueError("sort_order должен быть 'asc' или 'desc'")
        return v.lower() if v else v