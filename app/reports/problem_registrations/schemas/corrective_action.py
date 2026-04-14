from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.reports.enums import CorrectiveActionStatus


class CorrectiveActionCreate(BaseModel):
    document_id: int
    description: Optional[str] = None
    subtasks_text: Optional[str] = None
    responsible_user_id: Optional[int] = None
    responsible_department_id: Optional[int] = None
    due_date: Optional[datetime] = None
    status: CorrectiveActionStatus = CorrectiveActionStatus.NEW


class CorrectiveActionResponse(BaseModel):
    id: int
    document_id: int
    description: Optional[str] = None
    subtasks_text: Optional[str] = None
    responsible_user_id: Optional[int] = None
    responsible_department_id: Optional[int] = None
    due_date: Optional[datetime] = None
    status: CorrectiveActionStatus
    created_at: datetime

    class Config:
        from_attributes = True
