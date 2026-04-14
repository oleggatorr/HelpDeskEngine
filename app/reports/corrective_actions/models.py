from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CorrectiveAction(Base):
    __tablename__ = "corrective_actions"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    description = Column(Text)
    subtasks_text = Column(Text)
    responsible_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    responsible_department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(DateTime(timezone=True))
    status = Column(String(20), nullable=False, default="NEW")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    document = relationship("Document", backref="corrective_action")
    responsible_user = relationship("User", foreign_keys=[responsible_user_id])
    responsible_department = relationship("Department", foreign_keys=[responsible_department_id])

    execution = relationship(
        "ActionExecution",
        back_populates="corrective_action",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<CorrectiveAction {self.id}>"
