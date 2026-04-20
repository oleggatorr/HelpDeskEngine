from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class UserRole(str, PyEnum):
    ADMIN =     "admin"
    USER =      "user"
    QE =        "qe" 
    OWNER =     "owner"
    ASSIGNEE =  "assignee"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Связь 1 к 1 с UserProfile
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.login}>"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    role = Column(
        Enum(UserRole, values_callable=lambda e: [m.value for m in e]),
        default=UserRole.USER,
    )  # роль
    position = Column(String(100))  # должность
    permissions = Column(String(255))  # допуски (текстовое поле)

    # Связь 1 к 1 с User
    user = relationship("User", back_populates="profile")

    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True) # 👈 новое поле
    department = relationship("Department", back_populates="profiles")  # ← имя должно совпадать!



    def __repr__(self):
        return f"<UserProfile {self.role} - {self.position}>"
