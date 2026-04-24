from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class CorrectionActionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class CorrectionAction(Base):
    __tablename__ = "correction_actions"

    id = Column(Integer, primary_key=True, index=True, nullable=False)

    # 🔗 Связи (1:N к Correction)
    correction_id = Column(Integer, ForeignKey("corrections.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 👥 Назначение
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, 
                            comment="ID назначенного исполнителя")

    # 📝 Содержимое
    description = Column(Text, nullable=False, comment="Описание конкретного действия")
    status = Column(
        SAEnum(CorrectionActionStatus, name="correctionactionstatus",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=CorrectionActionStatus.PENDING,
        nullable=False
    )

    # ⏱️ Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Дата создания действия")
    assigned_at = Column(DateTime(timezone=True), nullable=True, comment="Дата назначения исполнителю")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="Дата фактического завершения")

    # 💬 Комментарий
    comment = Column(Text, nullable=True, comment="Дополнительный комментарий к выполнению или отклонению")

    # 🔗 Relationships
    correction = relationship("Correction", lazy="selectin")
    document = relationship("Document", lazy="selectin")
    assignee = relationship("User", foreign_keys=[assigned_user_id], lazy="selectin")

    def __repr__(self):
        return f"<CorrectionAction {self.id} - {self.status.value}>"