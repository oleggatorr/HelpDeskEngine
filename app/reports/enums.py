# app\reports\enums.py

from typing import Any, Optional
from typing_extensions import Annotated
from pydantic import BeforeValidator

from app.reports.documents.document_models import (
    DocumentStage, DocumentLanguage, DocumentPriority, DocumentStatus
)
from app.reports.correction.correction_models import CorrectionStatus
from app.reports.correction_action.ca_models import CorrectionActionStatus


# ========================
# UNIVERSAL ENUM PARSER
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
# COMMON ENUM FIELDS
# ========================

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

CorrectionStatusField = Annotated[
    Optional[CorrectionStatus],
    BeforeValidator(lambda v: parse_enum_safe(CorrectionStatus, v, None))
]

CorrectionActionStatusField = Annotated[
    Optional[CorrectionActionStatus],
    BeforeValidator(lambda v: parse_enum_safe(CorrectionActionStatus, v, None))
]