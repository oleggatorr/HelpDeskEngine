from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class MessageAttachmentCreate(BaseModel):
    """Схема создания вложения"""
    file_path: str
    original_filename: Optional[str] = None
    file_type: Optional[str] = None


class MessageAttachmentResponse(BaseModel):
    """Схема ответа вложения"""
    id: int
    file_path: str
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Схема создания сообщения"""
    chat_id: int
    content: str
    is_system: bool = False
    attachments: Optional[List[MessageAttachmentCreate]] = None


class MessageResponse(BaseModel):
    """Схема ответа сообщения"""
    id: int
    chat_id: int
    sender_id: Optional[int] = None
    sender_full_name: Optional[str] = None
    content: str
    is_system: bool = False
    created_at: datetime
    read_by_user_ids: List[int] = []
    attachments: List[MessageAttachmentResponse] = []

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Схема списка сообщений"""
    messages: List[MessageResponse]
    total: int


class MessageReadResponse(BaseModel):
    """Схема отметки прочтения"""
    message_id: int
    user_id: int
    read_at: datetime

    class Config:
        from_attributes = True
