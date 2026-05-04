# app/auth/permission_service.py

from fastapi import HTTPException, status
from app.auth.models import UserRole, UserProfile
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionDeniedException(HTTPException):
    def __init__(self, detail: str = "Доступ запрещен"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class PermissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================
    # ROLE & PERMISSION CHECKS (STATIC)
    # Не требуют состояния экземпляра или подключения к БД
    # ==========================================

    @staticmethod
    def _normalize_role(raw_role: Any) -> UserRole:
        if isinstance(raw_role, UserRole):
            return raw_role
        try:
            return UserRole(str(raw_role)) if raw_role else UserRole.USER
        except (ValueError, TypeError):
            return UserRole.USER

    @staticmethod
    def has_role(user: Any, role: UserRole) -> bool:
        if not user:
            return False
        profile = getattr(user, 'profile', None)
        raw_role = getattr(profile, 'role', None) if profile else None
        user_role = PermissionService._normalize_role(raw_role)

        if user_role == UserRole.ADMIN:
            return True
        return user_role == role

    @staticmethod
    def has_any_role(user: Any, roles: list[UserRole]) -> bool:
        return bool(user) and any(PermissionService.has_role(user, r) for r in roles)

    @staticmethod
    def require_role(user: Any, role: UserRole) -> None:
        if not PermissionService.has_role(user, role):
            raise PermissionDeniedException(f"Требуется роль: {role.value}")

    @staticmethod
    def require_any_role(user: Any, roles: list[UserRole]) -> None:
        if not PermissionService.has_any_role(user, roles):
            roles_str = ", ".join(r.value for r in roles)
            raise PermissionDeniedException(f"Требуется одна из ролей: {roles_str}")

    @staticmethod
    def _get_permissions(user: Any) -> Dict[str, List[str]]:
        if not user:
            return {}
        profile = getattr(user, 'profile', None)
        permissions = getattr(profile, 'permissions', None) if profile else None
        return permissions or {}

    @staticmethod
    def has_permission(user: Any, app: str, permission: str) -> bool:
        if not user:
            return False
        if PermissionService.has_role(user, UserRole.ADMIN):
            return True
        permissions = PermissionService._get_permissions(user)
        app_perms = permissions.get(app, [])
        return permission in app_perms

    @staticmethod
    def require_permission(user: Any, app: str, permission: str) -> None:
        if not PermissionService.has_permission(user, app, permission):
            raise PermissionDeniedException(f"Нет доступа: {app}:{permission}")

    # ==========================================
    # PERMISSION MANAGEMENT (INSTANCE METHODS)
    # Могут использовать self.db для сохранения в БД
    # ==========================================

    def add_app(self, profile: UserProfile, app: str) -> Dict[str, List[str]]:
        permissions = profile.permissions or {}
        print(permissions, app)
        if app in permissions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Приложение уже существует")
        permissions[app] = permissions.get(app, [])
        print(permissions)
        profile.permissions = permissions  # Важно для SQLAlchemy change tracking
        return permissions

    def remove_app(self, profile: UserProfile, app: str) -> Dict[str, List[str]]:
        permissions = profile.permissions or {}
        if app not in permissions:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приложение не найдено")
        del permissions[app]
        profile.permissions = permissions
        return permissions

    def add_permissions(self, profile: UserProfile, app: str, perms: List[str]) -> Dict[str, List[str]]:
        permissions = profile.permissions or {}
        if app not in permissions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Приложение не найдено")
        existing = set(permissions.get(app, []))
        existing.update(perms)
        permissions[app] = list(existing)
        profile.permissions = permissions
        return permissions

    def remove_permissions(self, profile: UserProfile, app: str, perms: List[str]) -> Dict[str, List[str]]:
        permissions = profile.permissions or {}
        if app not in permissions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Приложение не найдено")
        existing = set(permissions.get(app, []))
        existing -= set(perms)
        permissions[app] = list(existing)
        profile.permissions = permissions
        return permissions