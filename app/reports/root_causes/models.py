from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class RootCause(Base):
    __tablename__ = "root_causes"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    description = Column(Text)
    cause_code_id = Column(Integer, ForeignKey("cause_codes.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    document = relationship("Document", backref="root_cause")
    cause_code = relationship("CauseCode", backref="root_causes")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<RootCause {self.id}>"
