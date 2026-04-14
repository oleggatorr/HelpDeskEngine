from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator


class ChatCreate(BaseModel):
    """Схема создания чата"""
    name: Optional[str] = None
    document_id: Optional[int] = None
    participant_ids: List[int]  # ID пользователей


class ChatUpdate(BaseModel):
    """Схема обновления чата"""
    name: Optional[str] = None
    is_archived: Optional[bool] = False
    is_closed: Optional[bool] = False
    is_anonymized: Optional[bool] = False
    add_participant_ids: Optional[List[int]] = None
    remove_participant_ids: Optional[List[int]] = None


class ChatResponse(BaseModel):
    """Схема ответа чата"""
    id: int
    name: Optional[str] = None
    document_id: Optional[int] = None
    is_archived: bool = False
    is_closed: bool = False
    is_anonymized: bool = False
    participant_ids: List[int] = []
    created_at: datetime
    updated_at: datetime
    unread_count: int = 0

    class Config:
        from_attributes = True

    @field_validator("is_archived", "is_closed", "is_anonymized", mode="before")
    @classmethod
    def parse_bool_int(cls, v):
        if isinstance(v, int):
            return bool(v)
        return v


class ChatListResponse(BaseModel):
    """Схема списка чатов"""
    chats: List[ChatResponse]
    total: int


class ChatFilter(BaseModel):
    """Фильтры и сортировка для поиска чатов"""
    participant_id: Optional[int] = None
    document_id: Optional[int] = None
    name: Optional[str] = None
    is_archived: Optional[bool] = None
    is_closed: Optional[bool] = None
    is_anonymized: Optional[bool] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    sort_by: Optional[str] = "updated_at"
    sort_order: Optional[str] = "desc"

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        allowed = {"id", "name", "created_at", "updated_at", "document_id"}
        if v and v not in allowed:
            raise ValueError(f"sort_by должен быть одним из: {', '.join(allowed)}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        if v and v.lower() not in ("asc", "desc"):
            raise ValueError("sort_order должен быть 'asc' или 'desc'")
        return v.lower() if v else "desc"

    @field_validator("is_archived", "is_closed", "is_anonymized", mode="before")
    @classmethod
    def parse_bool_int(cls, v):
        if isinstance(v, int):
            return bool(v)
        return v
