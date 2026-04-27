from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text  # ❌ Убрали Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class CorrectionStatus(str, enum.Enum):
    """Статусы коррекции — значения .value хранятся в БД"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Correction(Base):
    __tablename__ = "corrections"

    id = Column(Integer, primary_key=True, index=True)

    # 🔗 Связи с документами и заявками
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_registration_id = Column(Integer, ForeignKey("problem_registrations.id", ondelete="CASCADE"), nullable=False, index=True)

    # 📝 Содержимое
    title = Column(String(200), nullable=False, comment="Краткое название корректирующего действия")
    description = Column(Text, nullable=True, comment="Описание отклонения/проблемы")
    corrective_action = Column(Text, nullable=False, comment="Фактически выполненные действия")
    
    # 🔥 БЫЛО: SAEnum(...) → СТАЛО: String с дефолтом .value
    status = Column(
        String(20),  # ✅ Достаточно для самого длинного значения "in_progress"
        default=CorrectionStatus.PLANNED.value,  # ✅ "planned", а не объект энума
        nullable=False
    )

    # 📅 Сроки
    planned_date = Column(DateTime(timezone=True), nullable=True, comment="Плановый срок выполнения")
    completed_date = Column(DateTime(timezone=True), nullable=True, comment="Фактическая дата выполнения")

    # ⏱️ Аудит — временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 👥 Аудит — пользователи
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="Создатель коррекции")
    completed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Исполнитель (завершил)")
    verified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Верификатор")

    # 🔗 Relationships
    document = relationship("Document")
    problem_registration = relationship("ProblemRegistration")
    
    # 👥 Relationships с User
    creator = relationship("User", foreign_keys=[created_by], lazy="selectin")
    completer = relationship("User", foreign_keys=[completed_by], lazy="selectin")
    verifier = relationship("User", foreign_keys=[verified_by], lazy="selectin")

    def __repr__(self):
        return f"<Correction {self.id} - {self.title}>"