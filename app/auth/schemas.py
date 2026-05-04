from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.auth.models import UserRole
from app.knowledge_base.schemas import DepartmentResponse


# ==========================================
# AUTH SCHEMAS
# ==========================================
class LoginRequest(BaseModel):
    login: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    login: str
    full_name: str
    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class TokenPayload(BaseModel):
    sub: int
    exp: datetime


# ==========================================
# USER SCHEMAS
# ==========================================
class UserBase(BaseModel):
    login: str
    full_name: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserProfileDTO(BaseModel):
    """Схема профиля пользователя"""
    id: int
    user_id: int
    role: Optional[UserRole] = None
    position: Optional[str] = None

    # ✅ JSON поле
    permissions: Optional[Dict[str, List[str]]] = None

    department_id: Optional[int] = None
    department: Optional[DepartmentResponse] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    login: str
    full_name: str
    email: str
    is_active: bool
    created_at: datetime
    profile: Optional[UserProfileDTO] = None

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    """Схема обновления профиля"""
    role: Optional[UserRole] = None
    position: Optional[str] = None

    # ✅ JSON поле
    permissions: Optional[Dict[str, List[str]]] = None

    department_id: Optional[int] = None


class UserFilter(BaseModel):
    """Фильтры для поиска пользователей"""
    login: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    position: Optional[str] = None

    # ⚠️ Фильтрация по JSON может потребовать доп. логики
    permissions: Optional[Dict[str, List[str]]] = None

    department_id: Optional[int] = None


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int

class AppPermissionRequest(BaseModel):
    app: str


class PermissionModifyRequest(BaseModel):
    app: str
    permissions: List[str]