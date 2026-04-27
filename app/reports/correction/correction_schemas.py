from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, field_validator
from datetime import datetime
from typing import Optional, List, Any
from typing_extensions import Annotated

# 🔗 Рекомендую импортировать из единого файла: from app.core.enums import ...
from app.reports.documents.document_models import DocumentStage, DocumentLanguage, DocumentPriority, DocumentStatus
from app.reports.correction.correction_models import CorrectionStatus


# ========================
# UNIVERSAL ENUM PARSER
# ========================

def parse_enum_safe(enum_cls, value: Any):
    """
    Принимает: enum-объект, .value (строку/число), или .name (для обратной совместимости).
    Возвращает: экземпляр enum или None.
    """
    if value is None or isinstance(value, enum_cls):
        return value
    
    # 1. Поиск по значению (основной случай: "open", 1, "planned")
    for member in enum_cls:
        if member.value == value or str(member.value) == str(value):
            return member
            
    # 2. Поиск по имени (обратная совместимость: "OPEN", "PLANNED")
    if isinstance(value, str):
        try:
            return enum_cls[value.upper()]
        except (KeyError, AttributeError):
            pass
            
    raise ValueError(f"Invalid value '{value}' for {enum_cls.__name__}")

# 🔧 Создаём переиспользуемые типы полей
StatusField = Annotated[Optional[CorrectionStatus], BeforeValidator(lambda v: parse_enum_safe(CorrectionStatus, v))]
DocStatusField = Annotated[Optional[DocumentStatus], BeforeValidator(lambda v: parse_enum_safe(DocumentStatus, v))]
DocLangField = Annotated[Optional[DocumentLanguage], BeforeValidator(lambda v: parse_enum_safe(DocumentLanguage, v))]
DocPriorityField = Annotated[Optional[DocumentPriority], BeforeValidator(lambda v: parse_enum_safe(DocumentPriority, v))]
DocStageField = Annotated[Optional[DocumentStage], BeforeValidator(lambda v: parse_enum_safe(DocumentStage, v))]


# ========================
# ВСПОМОГАТЕЛЬНЫЕ СХЕМЫ
# ========================

class AttachmentFileCreate(BaseModel):
    file_path: str = Field(..., examples=["/uploads/corrections/report_123.pdf"])
    file_type: str = Field(..., examples=["application/pdf"])
    original_filename: str = Field(..., examples=["отчёт_март_2026.pdf"])


# ========================
# CREATE
# ========================

class CorrectionCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)  # ✅ В сервис/БД уйдут .value

    problem_registration_id: int = Field(..., gt=0, description="ID заявки", examples=[123])
    title: str = Field(..., min_length=3, max_length=200, examples=["Некорректная валидация email"])
    description: Optional[str] = Field(None, examples=["Поля принимают адреса без @"])
    corrective_action: str = Field(..., min_length=3, examples=["Добавлена проверка формата"])
    
    # ✅ Используем Annotated-поля вместо ручных валидаторов
    status: StatusField = Field(default=CorrectionStatus.PLANNED, examples=["planned"])
    planned_date: Optional[datetime] = Field(None, examples=["2026-05-15T10:00:00Z"])
    completed_date: Optional[datetime] = Field(None, examples=["2026-05-10T14:30:00Z"])

    # Поля для авто-создания документа
    doc_status: DocStatusField = Field(default=DocumentStatus.OPEN, examples=["open"])
    doc_language: DocLangField = Field(default=DocumentLanguage.RU, examples=["ru"])
    doc_priority: DocPriorityField = Field(default=DocumentPriority.MEDIUM, examples=["medium"])

    attachment_files: Optional[List[AttachmentFileCreate]] = Field(default=None, description="Вложения")


# ========================
# UPDATE
# ========================

class CorrectionUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    title: Optional[str] = Field(None, min_length=3, max_length=200, examples=["Обновлённое название"])
    description: Optional[str] = Field(None, examples=["Дополнительные детали"])
    corrective_action: Optional[str] = Field(None, min_length=3, examples=["Новые действия"])
    status: StatusField = Field(None, examples=["in_progress"])
    planned_date: Optional[datetime] = Field(None, examples=["2026-06-01T09:00:00Z"])
    completed_date: Optional[datetime] = Field(None, examples=["2026-05-25T16:00:00Z"])


# ========================
# RESPONSE
# ========================

class CorrectionResponse(BaseModel):
    # ✅ from_attributes=True для чтения из ORM
    # ✅ use_enum_values=True для сериализации .value в JSON
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    document_id: int
    problem_registration_id: int

    # JOIN с Document
    track_id: Optional[str] = Field(None, examples=["TRK-2026-00123"])
    doc_created_at: Optional[datetime] = Field(None)
    doc_current_stage: Optional[int] = Field(None, examples=[1])  # ✅ IntEnum → int в БД
    doc_status: Optional[DocumentStatus] = Field(None, examples=["open"])
    is_locked: bool = False
    is_archived: bool = False
    assigned_to: Optional[int] = Field(None, examples=[42])

    # Собственные поля
    title: str
    description: Optional[str] = None
    corrective_action: str
    status: CorrectionStatus  # Сериализуется в "planned"/"completed"
    planned_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = Field(None)
    completed_by: Optional[int] = Field(None)
    verified_by: Optional[int] = Field(None)


# ========================
# LIST RESPONSE
# ========================

class CorrectionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    items: List[CorrectionResponse]
    total: int = Field(..., examples=[150])


# ========================
# FILTER
# ========================

class CorrectionFilter(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    # Фильтры по документу
    track_id: Optional[str] = Field(None, examples=["TRK-2026-"])
    doc_created_from: Optional[datetime] = Field(None)
    doc_created_to: Optional[datetime] = Field(None)
    doc_status: DocStatusField = Field(None, examples=["open"])
    doc_type_id: Optional[int] = Field(None, examples=[2])
    doc_current_stage: DocStageField = Field(None, examples=[2])
    created_by: Optional[int] = Field(None, examples=[1])
    assigned_to: Optional[int] = Field(None, examples=[42])
    is_locked: Optional[bool] = Field(None)

    # Фильтры по коррекции
    title: Optional[str] = Field(None, examples=["валидация"])
    status: StatusField = Field(None, examples=["planned"])
    planned_date_from: Optional[datetime] = Field(None)
    planned_date_to: Optional[datetime] = Field(None)
    description: Optional[str] = Field(None, examples=["ошибка"])

    # Пагинация
    page: int = Field(default=1, examples=[1])
    limit: int = Field(default=20, examples=[50])
    sort_by: str = Field(default="id", examples=["planned_date"])
    sort_order: str = Field(default="desc", examples=["asc"])

    # ✅ ПРАВИЛЬНЫЙ валидатор: @field_validator + имя поля + @classmethod
    @field_validator("sort_order", mode="before")
    @classmethod
    def validate_sort_order(cls, v: Optional[str]) -> str:
        if v and v.lower() not in ("asc", "desc"):
            return "desc"
        return v.lower() if v else "desc"