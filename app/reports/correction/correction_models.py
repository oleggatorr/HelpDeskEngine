from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Boolean, Text
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

    # 🔗 Связи с документами и заявками
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_registration_id = Column(Integer, ForeignKey("problem_registrations.id", ondelete="CASCADE"), nullable=False, unique=False, index=True)

    # 📝 Содержимое
    title = Column(String(200), nullable=False, comment="Краткое название корректирующего действия")
    description = Column(Text, nullable=True, comment="Описание отклонения/проблемы")
    corrective_action = Column(Text, nullable=False, comment="Фактически выполненные действия")
    status = Column(SAEnum(CorrectionStatus, name="correctionstatus",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls]), default=CorrectionStatus.PLANNED, nullable=False)

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

    # 🔗 Relationships — ⚠️ БЕЗ back_populates, т.к. обратная связь не объявлена в Document/ProblemRegistration
    document = relationship("Document")  # ← убрали back_populates="corrections"
    problem_registration = relationship("ProblemRegistration")  # ← убрали back_populates="correction"
    
    # 👥 Relationships с User
    creator = relationship("User", foreign_keys=[created_by], lazy="selectin")
    completer = relationship("User", foreign_keys=[completed_by], lazy="selectin")
    verifier = relationship("User", foreign_keys=[verified_by], lazy="selectin")

    def __repr__(self):
        return f"<Correction {self.id} - {self.title}>"