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
class DocumentStage(enum.Enum):
    NEW = 1
    IN_PROGRESS = 2
    WAITING = 3
    CLOSED = 4


# 🌐 Язык
class DocumentLanguage(str, enum.Enum):
    RU = "ru"
    EN = "en"
    CH = "ch"


# 🔥 Приоритет
class DocumentPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# 📋 Статус
class DocumentStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    CLOSED = "closed"
    REJECTED = "rejected"


class ProblemAction(enum.Enum):
    """Статусы обработки проблемы (значения должны точно совпадать с БД)"""
    UNDEFINED = "UNDEFINED"               
    REJECTED = "REJECTED"                 
    CLOSED = "CLOSED"                     
    ANALYSIS_REQUIRED = "ANALYSIS_REQUIRED"  
    ASSIGN_EXECUTOR = "ASSIGN_EXEC"    