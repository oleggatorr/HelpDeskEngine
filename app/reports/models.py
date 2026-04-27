import enum

# Импортируем справочники для корректного разрешения relationship
from app.knowledge_base.models import Department, Location, CauseCode  # noqa: F401

# Импортируем модели из доменов
from app.reports.documents.document_models import (  # noqa: F401
    Document, DocumentType, DocumentAttachment, DocumentLog,
)
from app.reports.problem_registrations.pr_models import ProblemRegistration  # noqa: F401

from app.reports.correction.correction_models import Correction
from app.reports.correction_action.ca_models import CorrectionAction



# 📊 Этап
class DocumentStage(enum.IntEnum):  # ✅ IntEnum для чисел
    NEW = 1
    IN_PROGRESS = 2
    WAITING = 3
    CLOSED = 4
    
    @classmethod
    def from_str(cls, value: str):
        """Конвертирует строку 'NEW' → DocumentStage.NEW"""
        mapping = {name: member for name, member in cls.__members__.items()}
        return mapping.get(value.upper())


# 🌐 DocumentLanguage — храним как String(2) в БД
class DocumentLanguage(str, enum.Enum):
    RU = "ru"
    EN = "en"
    CH = "ch"


# 🔥 DocumentPriority — храним как String(10) в БД
class DocumentPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# 📋 DocumentStatus — храним как String(20) в БД
class DocumentStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    CLOSED = "closed"
    REJECTED = "rejected"


# 🎯 ProblemAction — храним как String в БД (верхний регистр!)
class ProblemAction(str, enum.Enum):
    UNDEFINED = "UNDEFINED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"
    ANALYSIS_REQUIRED = "ANALYSIS_REQUIRED"
    ASSIGN_EXECUTOR = "ASSIGN_EXEC"


# 🔧 DecisionType — для коррекции
class DecisionType(str, enum.Enum):
    ANALYSIS = "ANALYSIS"
    ASSIGN = "ASSIGN"


# ✅ CorrectiveActionStatus — для действий по коррекции
class CorrectiveActionStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"