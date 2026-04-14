from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class RootCauseCreate(BaseModel):
    document_id: int
    description: Optional[str] = None
    cause_code_id: Optional[int] = None
    created_by: int


class RootCauseResponse(BaseModel):
    id: int
    document_id: int
    description: Optional[str] = None
    cause_code_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
