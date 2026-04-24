from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# Импортируем справочники для корректного разрешения relationship
from app.knowledge_base.models import Department, Location, CauseCode  # noqa: F401


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


# 📚 Справочник типов документов
class DocumentType(Base):
    __tablename__ = "document_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)

    documents = relationship("Document", back_populates="doc_type_ref")

    def __repr__(self):
        return f"<DocumentType {self.code}>"


# 🧩 Document
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(String(12), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(SAEnum(DocumentStatus), default=DocumentStatus.OPEN)
    doc_type_id = Column(Integer, ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True)
    current_stage = Column(SAEnum(DocumentStage), nullable=False, default=DocumentStage.NEW)
    is_locked = Column(Boolean, default=False, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    is_anonymized = Column(Boolean, default=False, nullable=False)
    language = Column(SAEnum(DocumentLanguage), default=DocumentLanguage.RU)
    priority = Column(SAEnum(DocumentPriority), default=DocumentPriority.MEDIUM)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    creator = relationship("User", foreign_keys=[created_by], backref="created_documents")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_documents")
    doc_type_ref = relationship("DocumentType", back_populates="documents")
    attachments = relationship("DocumentAttachment", back_populates="document", cascade="all, delete-orphan")
    logs = relationship("DocumentLog", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document {self.track_id}>"


# 📎 Вложения
class DocumentAttachment(Base):
    __tablename__ = "document_attachments"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    file_type = Column(String(255))
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False, nullable=False)

    document = relationship("Document", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<DocumentAttachment {self.id}>"


# 📝 Журнал изменений
class DocumentLog(Base):
    __tablename__ = "document_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(20), nullable=False)
    field_name = Column(String(50))
    old_value = Column(Text)
    new_value = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="logs")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<DocumentLog {self.document_id} - {self.action}>"
