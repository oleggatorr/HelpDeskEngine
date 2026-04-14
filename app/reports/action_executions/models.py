from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ActionExecution(Base):
    __tablename__ = "action_executions"

    id = Column(Integer, primary_key=True, index=True)

    corrective_action_id = Column(Integer, ForeignKey("corrective_actions.id", ondelete="CASCADE"), nullable=False, unique=True)
    comment = Column(Text)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True))

    # Связи
    corrective_action = relationship("CorrectiveAction", back_populates="execution")

    def __repr__(self):
        return f"<ActionExecution {self.id}>"
