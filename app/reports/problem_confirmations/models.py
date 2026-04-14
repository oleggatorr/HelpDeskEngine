from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ProblemConfirmation(Base):
    __tablename__ = "problem_confirmations"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)

    confirmed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision_type = Column(String(20), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    comment = Column(Text)
    is_rejected = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    document = relationship("Document", backref="problem_confirmation")
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    department = relationship("Department", backref="problem_confirmations")

    def __repr__(self):
        return f"<ProblemConfirmation {self.id}>"
