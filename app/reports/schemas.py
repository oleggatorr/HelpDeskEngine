from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


# ==========================================
# ENUMS
# ==========================================

class DocType(str, Enum):
    NC_REPORT = "NC_REPORT"
    NC_ANALYSIS = "NC_ANALYSIS"
    CORRECTIVE_ACTION = "CORRECTIVE_ACTION"


class DocStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"


# ==========================================
# DOCUMENT SCHEMAS
# ==========================================

class DocumentBase(BaseModel):
    """Базовая схема документа"""
    doc_type: DocType
    status: DocStatus = DocStatus.DRAFT


class DocumentCreate(DocumentBase):
    """Схема создания документа"""
    creator_id: int


class DocumentResponse(BaseModel):
    """Схема ответа документа"""
    id: int
    doc_type: DocType
    status: DocStatus
    creator_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Схема списка документов"""
    documents: List[DocumentResponse]
    total: int


# ==========================================
# NONCONFORMITY REPORT SCHEMAS
# ==========================================

class NonconformityReportCreate(BaseModel):
    """Схема создания отчета о несоответствии"""
    creator_id: int


class NonconformityReportResponse(BaseModel):
    """Схема ответа отчета о несоответствии"""
    id: int
    document: DocumentResponse

    class Config:
        from_attributes = True


# ==========================================
# NONCONFORMITY ANALYSIS SCHEMAS
# ==========================================

class NonconformityAnalysisCreate(BaseModel):
    """Схема создания анализа несоответствия"""
    creator_id: int


class NonconformityAnalysisResponse(BaseModel):
    """Схема ответа анализа несоответствия"""
    id: int
    document: DocumentResponse

    class Config:
        from_attributes = True


# ==========================================
# CORRECTIVE ACTION SCHEMAS
# ==========================================

class CorrectiveActionCreate(BaseModel):
    """Схема создания корректирующего действия"""
    creator_id: int


class CorrectiveActionResponse(BaseModel):
    """Схема ответа корректирующего действия"""
    id: int
    document: DocumentResponse

    class Config:
        from_attributes = True
