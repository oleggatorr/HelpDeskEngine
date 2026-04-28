# app/reports/correction_action/schemas.py

from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, field_validator
from datetime import datetime
from typing import Optional, List, Any, Literal
from typing_extensions import Annotated

from app.reports.documents.document_models import (
    DocumentStage, DocumentLanguage, DocumentPriority, DocumentStatus
)
from app.reports.correction_action.ca_models import CorrectionActionStatus


# ========================
# UNIVERSAL ENUM PARSER (SOFT MODE)
# ========================

def parse_enum_safe(enum_cls, value: Any, default=None, strict=False):
    if value is None or value == "":
        return default

    if isinstance(value, enum_cls):
        return value

    # match by value
    for member in enum_cls:
        if member.value == value or str(member.value) == str(value):
            return member

    # match by name
    if isinstance(value, str):
        try:
            return enum_cls[value.upper()]
        except (KeyError, AttributeError):
            pass

    if strict:
        raise ValueError(f"Invalid value '{value}' for {enum_cls.__name__}")

    return default


# ========================
# ENUM FIELDS
# ========================

ActionStatusField = Annotated[
    Optional[CorrectionActionStatus],
    BeforeValidator(lambda v: parse_enum_safe(CorrectionActionStatus, v, CorrectionActionStatus.PENDING))
]

DocStatusField = Annotated[
    Optional[DocumentStatus],
    BeforeValidator(lambda v: parse_enum_safe(DocumentStatus, v, DocumentStatus.OPEN))
]

DocLangField = Annotated[
    Optional[DocumentLanguage],
    BeforeValidator(lambda v: parse_enum_safe(DocumentLanguage, v, DocumentLanguage.RU))
]

DocPriorityField = Annotated[
    Optional[DocumentPriority],
    BeforeValidator(lambda v: parse_enum_safe(DocumentPriority, v, DocumentPriority.MEDIUM))
]


# =========================================================
# CREATE
# =========================================================

class CorrectionActionCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    correction_id: int = Field(..., gt=0)
    assigned_user_id: Optional[int] = Field(None, gt=0)

    description: str = Field(..., min_length=1, max_length=5000)
    comment: Optional[str] = Field(None, max_length=2000)

    # document auto-create
    doc_status: DocStatusField = Field(default=DocumentStatus.OPEN)
    doc_language: DocLangField = Field(default=DocumentLanguage.RU)
    doc_priority: DocPriorityField = Field(default=DocumentPriority.MEDIUM)
    doc_assigned_to: Optional[int] = Field(None, gt=0)


# =========================================================
# UPDATE
# =========================================================

class CorrectionActionUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    assigned_user_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)

    status: ActionStatusField = None
    comment: Optional[str] = Field(None, max_length=2000)


# =========================================================
# RESPONSE
# =========================================================

class CorrectionActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    correction_id: int
    document_id: int
    assigned_user_id: Optional[int]

    description: str
    status: CorrectionActionStatus
    comment: Optional[str]

    created_at: datetime
    assigned_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config["json_schema_extra"] = {
        "example": {
            "id": 1,
            "correction_id": 10,
            "document_id": 5,
            "assigned_user_id": 3,
            "description": "Провести RCA-анализ отклонения",
            "status": "in_progress",
            "comment": "Ожидание данных",
            "created_at": "2026-04-23T10:00:00+03:00",
            "assigned_at": "2026-04-23T10:05:00+03:00",
            "completed_at": None,
        }
    }


# =========================================================
# LIST RESPONSE
# =========================================================

class CorrectionActionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[CorrectionActionResponse]
    total: int
    limit: int
    offset: int


# =========================================================
# FILTER
# =========================================================

class CorrectionActionFilter(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    correction_id: Optional[int] = Field(None, gt=0)
    document_id: Optional[int] = Field(None, gt=0)
    assigned_user_id: Optional[int] = Field(None, gt=0)

    status: ActionStatusField = None

    description: Optional[str] = Field(None, max_length=100)
    comment: Optional[str] = Field(None, max_length=100)

    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None

    sort_by: Literal["id", "created_at", "status", "assigned_at"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, v):
        return parse_enum_safe(CorrectionActionStatus, v, None)