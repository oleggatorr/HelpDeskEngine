from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(255))
    doc_type = Column(String(20))
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Связь с User
    creator = relationship("User", backref="documents")

    def __repr__(self):
        return f"<Document {self.id} - {self.status}>"


class NonconformityReport(Base):
    """Отчет о несоответствии"""
    __tablename__ = "nonconformity_reports"

    id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)

    def __repr__(self):
        return f"<NonconformityReport {self.id}>"


class NonconformityAnalysis(Base):
    """Анализ несоответствия"""
    __tablename__ = "nonconformity_analyses"

    id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)

    def __repr__(self):
        return f"<NonconformityAnalysis {self.id}>"


class CorrectiveAction(Base):
    """Корректирующее действие"""
    __tablename__ = "corrective_actions"

    id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)

    def __repr__(self):
        return f"<CorrectiveAction {self.id}>"
