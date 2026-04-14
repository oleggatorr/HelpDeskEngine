from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.reports.enums import DecisionType


class ProblemConfirmationCreate(BaseModel):
    document_id: int
    confirmed_by: int
    decision_type: DecisionType
    department_id: Optional[int] = None
    comment: Optional[str] = None
    is_rejected: bool = False


class ProblemConfirmationResponse(BaseModel):
    id: int
    document_id: int
    confirmed_by: Optional[int] = None
    decision_type: DecisionType
    department_id: Optional[int] = None
    comment: Optional[str] = None
    is_rejected: bool
    created_at: datetime

    class Config:
        from_attributes = True
