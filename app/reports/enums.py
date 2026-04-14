from enum import Enum


class DocumentStage(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    CLOSED = "CLOSED"


class DecisionType(str, Enum):
    ANALYSIS = "ANALYSIS"
    ASSIGN = "ASSIGN"


class CorrectiveActionStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class DocumentLanguage(str, Enum):
    RU = "ru"
    EN = "en"


class DocumentPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DocumentStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    CLOSED = "closed"
    REJECTED = "rejected"
