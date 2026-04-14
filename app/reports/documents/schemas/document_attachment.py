from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class DocumentAttachmentCreate(BaseModel):
    document_id: int
    file_path: str
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    uploaded_by: int


class DocumentAttachmentResponse(BaseModel):
    id: int
    document_id: int
    file_path: str
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    uploaded_by: Optional[int] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True
