from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class CorrectionStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Correction(Base):
    __tablename__ = "corrections"

    id = Column(Integer, primary_key=True, index=True)

    # 🔗 Связи с документами
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), 
        nullable=False, index=True, 
        comment="Исходный документ (по которому выявлено отклонение)"
    )
    target_document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), 
        nullable=True, index=True,  # или False, если всегда должен быть назначен
        comment="Документ, на который назначена коррекция"
    )

    # 📝 Содержимое
    title = Column(String(200), nullable=False, comment="Краткое название корректирующего действия")
    description = Column(Text, nullable=True, comment="Описание отклонения/проблемы")
    corrective_action = Column(Text, nullable=False, comment="Фактически выполненные действия")
    
    status = Column(
        String(20),
        default=CorrectionStatus.PLANNED.value,
        nullable=False
    )

    # 📅 Сроки
    planned_date = Column(DateTime(timezone=True), nullable=True, comment="Плановый срок выполнения")
    completed_date = Column(DateTime(timezone=True), nullable=True, comment="Фактическая дата выполнения")

    # ⏱️ Аудит
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 👥 Аудит — пользователи
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    completed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # 🔗 Relationships
    document = relationship("Document", foreign_keys=[document_id], lazy="selectin")
    target_document = relationship("Document", foreign_keys=[target_document_id], lazy="selectin")
    
    creator = relationship("User", foreign_keys=[created_by], lazy="selectin")
    completer = relationship("User", foreign_keys=[completed_by], lazy="selectin")
    verifier = relationship("User", foreign_keys=[verified_by], lazy="selectin")

    def __repr__(self):
        return f"<Correction {self.id} - {self.title}>"