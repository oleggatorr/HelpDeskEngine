from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator
import re
import random
import string

from app.reports.enums import DocumentStage, DocumentLanguage, DocumentPriority, DocumentStatus

# Формат трек-номера: XXX-XXX-XXXX (3-4-3 символа, цифры + заглавные буквы)
TRACK_ID_PATTERN = re.compile(r"^[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{4}$")


def generate_track_id() -> str:
    """Генерация уникального трек-номера вида XXX-XXX-XXXX."""
    chars = string.ascii_uppercase + string.digits
    part1 = "".join(random.choices(chars, k=3))
    part2 = "".join(random.choices(chars, k=3))
    part3 = "".join(random.choices(chars, k=4))
    return f"{part1}-{part2}-{part3}"


class DocumentBase(BaseModel):
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

    @field_validator("current_stage", mode="before")
    @classmethod
    def parse_stage(cls, v):
        if isinstance(v, str):
            return DocumentStage[v]
        return v

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, v):
        if isinstance(v, str):
            return v
        return v

    @field_validator("language", "priority", mode="before")
    @classmethod
    def parse_enum_str(cls, v):
        if isinstance(v, str):
            return v
        return v

    @field_validator("track_id")
    @classmethod
    def validate_track_id(cls, v):
        if v is not None and not TRACK_ID_PATTERN.match(v):
            raise ValueError("track_id должен быть в формате XXX-XXXX-XXX (цифры и заглавные буквы)")
        return v


class DocumentCreate(DocumentBase):
    created_by: Optional[int] = 0
    attachment_files: Optional[List[dict]] = None  # [{"file_path": str, "file_type": str}]


class DocumentUpdate(BaseModel):
    status: Optional[DocumentStatus] = None
    doc_type_id: Optional[int] = None
    current_stage: Optional[DocumentStage] = None
    is_locked: Optional[bool] = False
    is_archived: Optional[bool] = False
    is_anonymized: Optional[bool] = False
    language: Optional[DocumentLanguage] = None
    priority: Optional[DocumentPriority] = None
    assigned_to: Optional[int] = None


class DocumentResponse(BaseModel):
    id: int
    track_id: str
    created_at: datetime
    created_by: Optional[int] = None
    status: DocumentStatus = DocumentStatus.OPEN
    doc_type_id: Optional[int] = None
    current_stage: str
    is_locked: bool = False
    is_archived: bool = False
    is_anonymized: bool = False
    language: DocumentLanguage = DocumentLanguage.RU
    priority: DocumentPriority = DocumentPriority.MEDIUM
    assigned_to: Optional[int] = None

    class Config:
        from_attributes = True

    @field_validator("current_stage", mode="before")
    @classmethod
    def parse_stage(cls, v):
        if isinstance(v, DocumentStage):
            return v.name
        return v

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, v):
        if isinstance(v, str):
            return v
        if hasattr(v, 'name'):
            return v.name
        if hasattr(v, 'value'):
            return v.value
        return str(v) if v else v

    @field_validator("language", "priority", mode="before")
    @classmethod
    def parse_enum_values(cls, v):
        if isinstance(v, str):
            return v
        if hasattr(v, 'name'):
            return v.name
        if hasattr(v, 'value'):
            return v.value
        return str(v) if v else v


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class DocumentFilter(BaseModel):
    """Фильтры для поиска документов"""
    track_id: Optional[str] = None
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    status: Optional[DocumentStatus] = None
    doc_type_id: Optional[int] = None
    current_stage: Optional[DocumentStage] = None
    is_locked: Optional[bool] = False
    is_archived: Optional[bool] = False
    is_anonymized: Optional[bool] = False
    language: Optional[DocumentLanguage] = None
    priority: Optional[DocumentPriority] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    sort_by: Optional[str] = "id"
    sort_order: Optional[str] = "desc"

    @field_validator("current_stage", mode="before")
    @classmethod
    def parse_stage(cls, v):
        if isinstance(v, str):
            return DocumentStage[v]
        return v

    @field_validator("language", "priority", mode="before")
    @classmethod
    def parse_enum_filters(cls, v):
        if isinstance(v, str):
            return v
        if hasattr(v, 'name'):
            return v.name
        return v

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        allowed = {"id", "track_id", "created_at", "created_by", "current_stage", "priority", "language"}
        if v and v not in allowed:
            raise ValueError(f"sort_by должен быть одним из: {', '.join(allowed)}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        if v and v.lower() not in ("asc", "desc"):
            raise ValueError("sort_order должен быть 'asc' или 'desc'")
        return v.lower() if v else "desc"
