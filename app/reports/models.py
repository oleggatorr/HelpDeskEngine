from sqlalchemy import Enum as SAEnum
from app.core.database import Base
import enum

# Импортируем справочники для корректного разрешения relationship
from app.knowledge_base.models import Department, Location, CauseCode  # noqa: F401

# Импортируем модели из доменов
from app.reports.documents.models import (  # noqa: F401
    Document, DocumentType, DocumentAttachment, DocumentLog,
)
from app.reports.problem_registrations.models import ProblemRegistration  # noqa: F401
from app.reports.root_causes.models import RootCause  # noqa: F401
from app.reports.corrective_actions.models import CorrectiveAction  # noqa: F401
from app.reports.action_executions.models import ActionExecution  # noqa: F401


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
