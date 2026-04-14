from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # Механический цех, Сборочный и т.д.

    def __repr__(self):
        return f"<Department {self.name}>"


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # Цех/Участок/Станция

    def __repr__(self):
        return f"<Location {self.name}>"


class CauseCode(Base):
    __tablename__ = "cause_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(Text)

    def __repr__(self):
        return f"<CauseCode {self.code}>"
