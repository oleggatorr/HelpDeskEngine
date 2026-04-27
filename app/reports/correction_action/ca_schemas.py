# app/reports/correction_action/schemas.py
"""Схемы Pydantic для действий по коррекции."""

from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, field_validator
from datetime import datetime
from typing import Optional, List, Any, Literal
from typing_extensions import Annotated

# 🔗 Единый источник энумов (убираем дубликаты!)
from app.reports.documents.document_models import DocumentStage, DocumentLanguage, DocumentPriority, DocumentStatus
from app.reports.correction_action.ca_models import CorrectionActionStatus


# ========================
# UNIVERSAL ENUM PARSER
# ========================

def parse_enum_safe(enum_cls, value: Any):
    """
    Универсальный парсер: принимает .value, .name, или уже готовый enum.
    Возвращает экземпляр enum или None.
    """
    if value is None or isinstance(value, enum_cls):
        return value
    
    # 1. Поиск по значению (основной: "pending", "completed")
    for member in enum_cls:
        if member.value == value or str(member.value) == str(value):
            return member
            
    # 2. Поиск по имени (обратная совместимость: "PENDING")
    if isinstance(value, str):
        try:
            return enum_cls[value.upper()]
        except (KeyError, AttributeError):
            pass
            
    raise ValueError(f"Invalid value '{value}' for {enum_cls.__name__}")


# 🔧 Переиспользуемые типы полей через Annotated
ActionStatusField = Annotated[Optional[CorrectionActionStatus], BeforeValidator(lambda v: parse_enum_safe(CorrectionActionStatus, v))]
DocStatusField = Annotated[Optional[DocumentStatus], BeforeValidator(lambda v: parse_enum_safe(DocumentStatus, v))]
DocLangField = Annotated[Optional[DocumentLanguage], BeforeValidator(lambda v: parse_enum_safe(DocumentLanguage, v))]
DocPriorityField = Annotated[Optional[DocumentPriority], BeforeValidator(lambda v: parse_enum_safe(DocumentPriority, v))]


# =========================================================
# 📥 CREATE
# =========================================================

class CorrectionActionCreate(BaseModel):
    """Создание корректирующего действия."""
    model_config = ConfigDict(use_enum_values=True)  # ✅ В сервис/БД уйдут .value

    correction_id: int = Field(..., gt=0, description="ID родительской коррекции")
    assigned_user_id: Optional[int] = Field(None, gt=0, description="ID исполнителя")
    description: str = Field(..., min_length=1, max_length=5000)
    comment: Optional[str] = Field(None, max_length=2000)

    # Поля Document (создаётся автоматически) — используем Annotated-поля
    doc_status: DocStatusField = Field(default=DocumentStatus.OPEN)
    doc_language: DocLangField = Field(default=DocumentLanguage.RU)
    doc_priority: DocPriorityField = Field(default=DocumentPriority.MEDIUM)
    doc_assigned_to: Optional[int] = Field(None, gt=0)


# =========================================================
# ✏️ UPDATE (PATCH)
# =========================================================

class CorrectionActionUpdate(BaseModel):
    """Частичное обновление."""
    model_config = ConfigDict(use_enum_values=True)

    assigned_user_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    status: ActionStatusField = Field(None)  # ✅ Гибкий парсинг: "pending", "PENDING", или энум
    comment: Optional[str] = Field(None, max_length=2000)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        """Доп. валидация, если нужна специфичная логика"""
        return parse_enum_safe(CorrectionActionStatus, v)


# =========================================================
# 📤 RESPONSE
# =========================================================

class CorrectionActionResponse(BaseModel):
    """Ответ клиенту"""
    # ✅ from_attributes=True для чтения из ORM
    # ✅ use_enum_values=True для сериализации .value в JSON
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    correction_id: int
    document_id: int
    assigned_user_id: Optional[int]

    description: str
    status: CorrectionActionStatus  # ✅ Сериализуется в "pending"/"in_progress"
    comment: Optional[str]

    created_at: datetime
    assigned_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Пример для OpenAPI docs
    model_config["json_schema_extra"] = {
        "example": {
            "id": 1,
            "correction_id": 10,
            "document_id": 5,
            "assigned_user_id": 3,
            "description": "Провести RCA-анализ отклонения",
            "status": "in_progress",  # ✅ строка, не объект Enum
            "comment": "Ожидание данных от лаборатории",
            "created_at": "2026-04-23T10:00:00+03:00",
            "assigned_at": "2026-04-23T10:05:00+03:00",
            "completed_at": None,
        }
    }


# =========================================================
# 📄 LIST RESPONSE
# =========================================================

class CorrectionActionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    items: List[CorrectionActionResponse]
    total: int
    limit: int
    offset: int


# =========================================================
# 🔍 FILTER
# =========================================================

class CorrectionActionFilter(BaseModel):
    """Фильтры списка"""
    # ❌ УБРАНО: from_attributes=True — не нужен для входных данных
    
    correction_id: Optional[int] = Field(None, gt=0)
    document_id: Optional[int] = Field(None, gt=0)
    assigned_user_id: Optional[int] = Field(None, gt=0)

    status: ActionStatusField = Field(None)  # ✅ Гибкий парсинг

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