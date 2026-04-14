from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProblemRegistration(Base):
    __tablename__ = "problem_registrations"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    detected_at = Column(DateTime(timezone=True))
    subject = Column(String(200))
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text)
    nomenclature = Column(String(100), nullable=True)

    # Связи
    document = relationship("Document", backref="problem_registration")
    location = relationship("Location", backref="problem_registrations")

    def __repr__(self):
        return f"<ProblemRegistration {self.id}>"
