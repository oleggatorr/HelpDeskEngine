from pydantic import BaseModel, ConfigDict, field_validator, Field
from datetime import datetime
from typing import Optional, List

from app.reports.enums import DocumentStatus, DocumentLanguage, DocumentPriority
from app.reports.correction.models import CorrectionStatus


# 📎 Вспомогательная схема для вложений (вместо List[dict])
class AttachmentFileCreate(BaseModel):
    file_path: str = Field(..., examples=["/uploads/corrections/report_123.pdf"])
    file_type: str = Field(..., examples=["application/pdf"])
    original_filename: str = Field(..., examples=["отчёт_март_2026.pdf"])


class CorrectionCreate(BaseModel):
    """Схема создания корректирующего действия."""
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    # 🔗 Обязательная связь с заявкой
    problem_registration_id: int = Field(
        ..., 
        gt=0, 
        description="ID заявки (ProblemRegistration), к которой применяется коррекция",
        examples=[123]
    )

    # 📝 Содержимое коррекции
    title: str = Field(
        ..., 
        min_length=3, 
        max_length=200, 
        description="Краткое название корректирующего действия",
        examples=["Некорректная валидация email-адресов"]
    )
    description: Optional[str] = Field(
        None, 
        description="Описание отклонения/проблемы",
        examples=["Поля принимают адреса без символа @"]
    )
    corrective_action: str = Field(
        ..., 
        min_length=3, 
        description="Фактически выполненные действия",
        examples=["Добавлена проверка формата email на уровне API и UI"]
    )
    
    # 📊 Статус и сроки
    status: CorrectionStatus = Field(
        default=CorrectionStatus.PLANNED, 
        description="Текущий статус",
        examples=["planned"]
    )
    planned_date: Optional[datetime] = Field(
        None, 
        description="Плановый срок выполнения",
        examples=["2026-05-15T10:00:00Z"]
    )
    completed_date: Optional[datetime] = Field(
        None, 
        description="Фактическая дата выполнения",
        examples=["2026-05-10T14:30:00Z"]
    )

    # 📄 Поля для авто-создания документа (передаются в DocumentService)
    doc_status: DocumentStatus = Field(
        default=DocumentStatus.OPEN, 
        description="Статус создаваемого документа",
        examples=["open"]
    )
    doc_language: DocumentLanguage = Field(
        default=DocumentLanguage.RU, 
        description="Язык документа",
        examples=["ru"]
    )
    doc_priority: DocumentPriority = Field(
        default=DocumentPriority.MEDIUM, 
        description="Приоритет документа",
        examples=["medium"]
    )
    doc_assigned_to: Optional[int] = Field(
        None, 
        description="ID пользователя, которому назначается документ",
        examples=[42]
    )

    # 📎 Вложения — теперь с типизированной схемой
    attachment_files: Optional[List[AttachmentFileCreate]] = Field(
        default=None, 
        description="Список вложений",
        examples=[[
            {
                "file_path": "/uploads/corrections/fix_email.pdf",
                "file_type": "application/pdf",
                "original_filename": "инструкция_по_фиксу.pdf"
            }
        ]]
    )

    # 🔧 Валидатор для status
    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        if v is None:
            return CorrectionStatus.PLANNED
        if isinstance(v, str):
            v = v.lower().strip()  # "PLANNED" → "planned"
        # Pydantic сам сконвертирует строку в Enum, если она совпадает с .value
        return v

    @field_validator("doc_status", "doc_language", "doc_priority", mode="before")
    @classmethod
    def parse_doc_enums(cls, v, info):
        from app.reports.enums import DocumentStatus, DocumentLanguage, DocumentPriority
        enum_map = {
            "doc_status": DocumentStatus,
            "doc_language": DocumentLanguage,
            "doc_priority": DocumentPriority,
        }
        field_name = info.field_name
        enum_cls = enum_map.get(field_name)
        if not enum_cls or v is None or v == "":
            return v
        if isinstance(v, enum_cls):
            return v
        if isinstance(v, str):
            try:
                return enum_cls(v)
            except ValueError:
                return v
        return v


class CorrectionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200, examples=["Обновлённое название"])
    description: Optional[str] = Field(None, examples=["Дополнительные детали"])
    corrective_action: Optional[str] = Field(None, min_length=3, examples=["Новые действия"])
    status: Optional[CorrectionStatus] = Field(None, examples=["in_progress"])
    planned_date: Optional[datetime] = Field(None, examples=["2026-06-01T09:00:00Z"])
    completed_date: Optional[datetime] = Field(None, examples=["2026-05-25T16:00:00Z"])


class CorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    problem_registration_id: int

    # Данные из JOIN с Document
    track_id: Optional[str] = Field(None, examples=["TRK-2026-00123"])
    doc_created_at: Optional[datetime] = Field(None, examples=["2026-04-01T08:00:00Z"])
    doc_current_stage: Optional[str] = Field(None, examples=["review"])
    doc_status: Optional[DocumentStatus] = Field(None, examples=["open"])
    is_locked: bool = Field(default=False)
    is_archived: bool = Field(default=False)
    assigned_to: Optional[int] = Field(None, examples=[42])

    # Собственные поля
    title: str
    description: Optional[str] = None
    corrective_action: str
    status: CorrectionStatus
    planned_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime
    is_deleted: bool = Field(default=False)
    created_by: Optional[int] = Field(None, examples=[1])
    completed_by: Optional[int] = Field(None, examples=[5])
    verified_by: Optional[int] = Field(None, examples=[3])


class CorrectionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    items: List[CorrectionResponse]
    total: int = Field(..., examples=[150])


class CorrectionFilter(BaseModel):
    # Фильтры по документу
    track_id: Optional[str] = Field(None, examples=["TRK-2026-"])
    doc_created_from: Optional[datetime] = Field(None, examples=["2026-01-01T00:00:00Z"])
    doc_created_to: Optional[datetime] = Field(None, examples=["2026-12-31T23:59:59Z"])
    doc_status: Optional[DocumentStatus] = Field(None, examples=["open"])
    doc_type_id: Optional[int] = Field(None, examples=[2])
    doc_current_stage: Optional[str] = Field(None, examples=["approval"])
    created_by: Optional[int] = Field(None, examples=[1])
    assigned_to: Optional[int] = Field(None, examples=[42])
    is_locked: Optional[bool] = Field(None, examples=[False])

    # Фильтры по коррекции
    title: Optional[str] = Field(None, examples=["валидация"])
    status: Optional[CorrectionStatus] = Field(None, examples=["planned"])
    planned_date_from: Optional[datetime] = Field(None, examples=["2026-04-01T00:00:00Z"])
    planned_date_to: Optional[datetime] = Field(None, examples=["2026-06-30T23:59:59Z"])
    description: Optional[str] = Field(None, examples=["ошибка"])

    # Пагинация и сортировка
    page: int = Field(default=1, examples=[1])
    limit: int = Field(default=20, examples=[50])
    sort_by: str = Field(default="id", examples=["planned_date"])
    sort_order: str = Field(default="desc", examples=["asc"])

    @field_validator("sort_order", mode="before")
    @classmethod
    def validate_sort_order(cls, v):
        if v and v.lower() not in ("asc", "desc"):
            return "desc"
        return v.lower() if v else "desc"