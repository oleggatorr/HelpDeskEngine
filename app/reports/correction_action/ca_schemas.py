from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import datetime
from typing import Optional, List, Literal
import enum
from app.reports.enums import DocumentStatus, DocumentLanguage, DocumentPriority


# 🔹 Лучше держать enum отдельно (но можно и тут)
class CorrectionActionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


# =========================================================
# 📥 CREATE
# =========================================================
class CorrectionActionCreate(BaseModel):
    """Создание корректирующего действия.
    ⚠️ Статус всегда выставляется сервером (PENDING).
    """
    correction_id: int = Field(..., description="ID родительской коррекции")
    assigned_user_id: Optional[int] = Field(None, description="ID исполнителя")
    description: str = Field(..., min_length=1, max_length=5000)
    comment: Optional[str] = Field(None, max_length=2000)

        # Поля Document (создаётся автоматически)
    doc_status: Optional[DocumentStatus] = DocumentStatus.OPEN
    doc_language: Optional[DocumentLanguage] = DocumentLanguage.RU
    doc_priority: Optional[DocumentPriority] = DocumentPriority.MEDIUM
    doc_assigned_to: Optional[int] = None


# =========================================================
# ✏️ UPDATE (PATCH)
# =========================================================
class CorrectionActionUpdate(BaseModel):
    """Частичное обновление.
    ⏱️ Таймстемпы управляются сервисом.
    """
    assigned_user_id: Optional[int] = None
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    status: Optional[CorrectionActionStatus] = None
    comment: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def check_not_empty(self):
        if not any(
            value is not None
            for value in [
                self.assigned_user_id,
                self.description,
                self.status,
                self.comment,
            ]
        ):
            raise ValueError("At least one field must be provided for update")
        return self


# =========================================================
# 📤 RESPONSE
# =========================================================
class CorrectionActionResponse(BaseModel):
    """Ответ клиенту"""
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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "correction_id": 10,
                "document_id": 5,
                "assigned_user_id": 3,
                "description": "Провести RCA-анализ отклонения",
                "status": "in_progress",
                "comment": "Ожидание данных от лаборатории",
                "created_at": "2026-04-23T10:00:00+03:00",
                "assigned_at": "2026-04-23T10:05:00+03:00",
                "completed_at": None,
            }
        },
    )


# =========================================================
# 📄 LIST RESPONSE (с пагинацией)
# =========================================================
class CorrectionActionListResponse(BaseModel):
    items: List[CorrectionActionResponse]
    total: int
    limit: int
    offset: int


# =========================================================
# 🔍 FILTER
# =========================================================
class CorrectionActionFilter(BaseModel):
    """Фильтры списка"""

    correction_id: Optional[int] = None
    document_id: Optional[int] = None
    assigned_user_id: Optional[int] = None

    status: Optional[CorrectionActionStatus] = None

    description: Optional[str] = Field(
        None,
        max_length=100,
        description="Поиск по описанию (ILIKE %...%)",
    )

    comment: Optional[str] = Field(
        None,
        max_length=100,
        description="Поиск по комментарию (ILIKE %...%)",
    )

    created_from: Optional[datetime] = Field(None, description=">= created_at")
    created_to: Optional[datetime] = Field(None, description="<= created_at")

    # ✅ безопасная сортировка
    sort_by: Literal["id", "created_at", "status", "assigned_at"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"

    # ✅ пагинация
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

    model_config = ConfigDict(from_attributes=True)