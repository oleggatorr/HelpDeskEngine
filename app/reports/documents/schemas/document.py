from typing import Optional, List
from datetime import datetime
import re
import random
import string

from pydantic import BaseModel, field_validator, ConfigDict

from app.reports.enums import (
    DocumentStage,
    DocumentLanguage,
    DocumentPriority,
    DocumentStatus,
)

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
# ENUM PARSER (DRY)
# ========================

def parse_enum(enum_cls, value):
    if value is None or isinstance(value, enum_cls):
        return value

    if isinstance(value, str):
        try:
            return enum_cls[value.upper()]
        except KeyError:
            raise ValueError(f"Invalid value '{value}' for {enum_cls.__name__}")

    return value


# ========================
# CREATE
# ========================

class DocumentCreate(BaseModel):
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
    attachment_files: Optional[List[dict]] = None  # ⚠ можно улучшить отдельной схемой

    @field_validator("track_id")
    @classmethod
    def validate_track_id(cls, v):
        if v and not TRACK_ID_PATTERN.match(v):
            raise ValueError("track_id должен быть в формате XXX-XXX-XXXX")
        return v

    # универсальный парсинг
    _parse_stage = field_validator("current_stage", mode="before")(lambda cls, v: parse_enum(DocumentStage, v))
    _parse_status = field_validator("status", mode="before")(lambda cls, v: parse_enum(DocumentStatus, v))
    _parse_language = field_validator("language", mode="before")(lambda cls, v: parse_enum(DocumentLanguage, v))
    _parse_priority = field_validator("priority", mode="before")(lambda cls, v: parse_enum(DocumentPriority, v))


# ========================
# UPDATE
# ========================

class DocumentUpdate(BaseModel):
    status: Optional[DocumentStatus] = None
    doc_type_id: Optional[int] = None
    current_stage: Optional[DocumentStage] = None
    is_locked: Optional[bool] = None
    is_archived: Optional[bool] = None
    is_anonymized: Optional[bool] = None
    language: Optional[DocumentLanguage] = None
    priority: Optional[DocumentPriority] = None
    assigned_to: Optional[int] = None

    _parse_stage = field_validator("current_stage", mode="before")(lambda cls, v: parse_enum(DocumentStage, v))
    _parse_status = field_validator("status", mode="before")(lambda cls, v: parse_enum(DocumentStatus, v))
    _parse_language = field_validator("language", mode="before")(lambda cls, v: parse_enum(DocumentLanguage, v))
    _parse_priority = field_validator("priority", mode="before")(lambda cls, v: parse_enum(DocumentPriority, v))


# ========================
# RESPONSE
# ========================

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    track_id: str
    created_at: datetime
    created_by: Optional[int] = None
    status: str
    doc_type_id: Optional[int] = None
    current_stage: str
    is_locked: bool
    is_archived: bool
    is_anonymized: bool
    language: str
    priority: str
    assigned_to: Optional[int] = None

    @field_validator("status", "current_stage", "language", "priority", mode="before")
    @classmethod
    def enum_to_str(cls, v):
        if hasattr(v, "name"):
            return v.name.lower()
        return v


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

    _parse_stage = field_validator("current_stage", mode="before")(lambda cls, v: parse_enum(DocumentStage, v))
    _parse_status = field_validator("status", mode="before")(lambda cls, v: parse_enum(DocumentStatus, v))
    _parse_language = field_validator("language", mode="before")(lambda cls, v: parse_enum(DocumentLanguage, v))
    _parse_priority = field_validator("priority", mode="before")(lambda cls, v: parse_enum(DocumentPriority, v))

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
        if v.lower() not in ("asc", "desc"):
            raise ValueError("sort_order должен быть 'asc' или 'desc'")
        return v.lower()