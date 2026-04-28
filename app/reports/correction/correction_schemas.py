from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, field_validator
from datetime import datetime
from typing import Optional, List, Any
from typing_extensions import Annotated

from app.reports.documents.document_models import (
    DocumentStage, DocumentLanguage, DocumentPriority, DocumentStatus
)
from app.reports.correction.correction_models import CorrectionStatus


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
# REUSABLE ENUM FIELDS
# ========================

StatusField = Annotated[
    Optional[CorrectionStatus],
    BeforeValidator(lambda v: parse_enum_safe(CorrectionStatus, v, CorrectionStatus.PLANNED))
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

DocStageField = Annotated[
    Optional[DocumentStage],
    BeforeValidator(lambda v: parse_enum_safe(DocumentStage, v, None))
]


# ========================
# ATTACHMENT
# ========================

class AttachmentFileCreate(BaseModel):
    file_path: str = Field(..., examples=["/uploads/corrections/report_123.pdf"])
    file_type: str = Field(..., examples=["application/pdf"])
    original_filename: str = Field(..., examples=["report_march_2026.pdf"])


# ========================
# CREATE
# ========================

class CorrectionCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    problem_registration_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    corrective_action: str = Field(..., min_length=3)

    status: StatusField = Field(default=CorrectionStatus.PLANNED)
    planned_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None

    # document auto-create
    doc_status: DocStatusField = Field(default=DocumentStatus.OPEN)
    doc_language: DocLangField = Field(default=DocumentLanguage.RU)
    doc_priority: DocPriorityField = Field(default=DocumentPriority.MEDIUM)

    attachment_files: Optional[List[AttachmentFileCreate]] = None


# ========================
# UPDATE
# ========================

class CorrectionUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    corrective_action: Optional[str] = Field(None, min_length=3)

    status: StatusField = None
    planned_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None


# ========================
# RESPONSE
# ========================

class CorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    document_id: int
    problem_registration_id: int

    # document (join)
    track_id: Optional[str] = None
    doc_created_at: Optional[datetime] = None
    doc_current_stage: Optional[DocumentStage] = None
    doc_status: Optional[DocumentStatus] = None
    is_locked: bool = False
    is_archived: bool = False
    assigned_to: Optional[int] = None

    # correction
    title: str
    description: Optional[str] = None
    corrective_action: str
    status: CorrectionStatus
    planned_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    completed_by: Optional[int] = None
    verified_by: Optional[int] = None


# ========================
# LIST RESPONSE
# ========================

class CorrectionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[CorrectionResponse]
    total: int


# ========================
# FILTER
# ========================

class CorrectionFilter(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    # document filters
    track_id: Optional[str] = None
    doc_created_from: Optional[datetime] = None
    doc_created_to: Optional[datetime] = None
    doc_status: DocStatusField = None
    doc_type_id: Optional[int] = None
    doc_current_stage: DocStageField = None
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    is_locked: Optional[bool] = None

    # correction filters
    title: Optional[str] = None
    status: StatusField = None
    planned_date_from: Optional[datetime] = None
    planned_date_to: Optional[datetime] = None
    description: Optional[str] = None

    # pagination
    page: int = 1
    limit: int = 20

    # sorting
    sort_by: str = "id"
    sort_order: str = "desc"

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        allowed = {
            "id", "title", "status",
            "planned_date", "created_at"
        }
        return v if v in allowed else "id"

    @field_validator("sort_order", mode="before")
    @classmethod
    def validate_sort_order(cls, v):
        if v and v.lower() not in ("asc", "desc"):
            return "desc"
        return v.lower() if v else "desc"

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