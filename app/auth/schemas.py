from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.auth.models import UserRole


# ==========================================
# AUTH SCHEMAS
# ==========================================

class LoginRequest(BaseModel):
    """Схема запроса входа"""
    login: str
    password: str


class LoginResponse(BaseModel):
    """Схема ответа с токенами"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    """Схема запроса регистрации"""
    login: str
    full_name: str
    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    """Схема запроса смены пароля"""
    old_password: str
    new_password: str


class TokenPayload(BaseModel):
    """Схема payload токена"""
    sub: int  # user_id
    exp: datetime


# ==========================================
# USER SCHEMAS
# ==========================================

class UserBase(BaseModel):
    """Базовая схема пользователя"""
    login: str
    full_name: str
    email: EmailStr


class UserCreate(UserBase):
    """Схема создания пользователя"""
    password: str


class UserUpdate(BaseModel):
    """Схема обновления пользователя"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Схема ответа пользователя"""
    id: int
    login: str
    full_name: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileDTO(BaseModel):
    """Схема профиля пользователя"""
    id: int
    user_id: int
    role: Optional[UserRole] = None
    position: Optional[str] = None
    permissions: Optional[str] = None

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    """Схема обновления профиля"""
    role: Optional[UserRole] = None
    position: Optional[str] = None
    permissions: Optional[str] = None


class UserFilter(BaseModel):
    """Фильтры для поиска пользователей"""
    login: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    position: Optional[str] = None
    permissions: Optional[str] = None


class UserListResponse(BaseModel):
    """Схема списка пользователей"""
    users: List[UserResponse]
    total: int
