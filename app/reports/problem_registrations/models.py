from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, text
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class ProblemAction(enum.Enum):
    """Статусы обработки проблемы (значения должны точно совпадать с БД)"""
    UNDEFINED = "UNDEFINED"               
    REJECTED = "REJECTED"                 
    CLOSED = "CLOSED"                     
    ANALYSIS_REQUIRED = "ANALYSIS_REQUIRED"  
    ASSIGN_EXECUTOR = "ASSIGN_EXEC"    
    
    @property
    def is_final(self) -> bool:
        return self in (ProblemAction.REJECTED, ProblemAction.CLOSED)
    
    @classmethod
    def get_labels(cls) -> dict:
        return {
            "undefined": "Не определено",
            "rejected": "Отклонить",
            "closed": "Закрыть",
            "analysis_required": "Требуется анализ",
            "assign_executor": "Назначить исполнителя",
        }
    
    @classmethod
    def get_choices(cls) -> list[dict]:
        return [{"value": v, "label": l} for v, l in cls.get_labels().items()]


class ProblemRegistration(Base):
    __tablename__ = "problem_registrations"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    detected_at = Column(DateTime(timezone=True))
    subject = Column(String(200))
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text)
    nomenclature = Column(String(100), nullable=True)

    '''Данные после подтверждения'''
    approved_at = Column(DateTime(timezone=True), nullable=True, comment="Дата утверждения")
    
    # 👇 ИСПРАВЛЕНО: server_default теперь совпадает с английским значением enum
    action = Column(
        SAEnum(ProblemAction, name="problem_action_enum", create_constraint=True),
        nullable=True, 
        server_default=text("'analysis_required'"),  # Английский value + безопасное экранирование
        comment="Действие по проблеме"
    )
    
    responsible_department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="ID ответственного отделения")
    comment = Column(Text, nullable=True, comment="Комментарий к проблеме")

    # Связи
    document = relationship("Document", backref="problem_registration")
    location = relationship("Location", backref="problem_registrations")
    responsible_department = relationship("Department", backref="problem_registrations")

    def __repr__(self):
        return f"<ProblemRegistration {self.id}>"