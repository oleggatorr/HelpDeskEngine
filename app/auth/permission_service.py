from fastapi import HTTPException, status
from app.auth.models import User, UserRole
from typing import Any



class PermissionDeniedException(HTTPException):
    def __init__(self, detail: str = "Доступ запрещен"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class PermissionService:
    @staticmethod
    def _normalize_role(raw_role: Any) -> UserRole:
        """Безопасно приводит значение из БД/DTO к UserRole."""
        if isinstance(raw_role, UserRole):
            return raw_role
        try:
            # str() работает и для "admin", и для UserRole.ADMIN
            return UserRole(str(raw_role)) if raw_role else UserRole.USER
        except (ValueError, TypeError):
            # Если в БД попал неизвестный статус, считаем его обычным юзером
            return UserRole.USER

    @staticmethod
    def has_role(user: Any, role: UserRole) -> bool:
        if not user:
            return False
            
        profile = getattr(user, 'profile', None)
        raw_role = getattr(profile, 'role', None) if profile else None
        user_role = PermissionService._normalize_role(raw_role)
        
        # Админ имеет все роли
        if user_role == UserRole.ADMIN:
            return True
            
        # Сравниваем напрямую (UserRole наследуется от str)
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
    def has_permission(user: Any, permission: str) -> bool:
        """Проверка прав. Предполагает, что поле permissions хранит список через запятую."""
        if not user:
            return False
        profile = getattr(user, 'profile', None)
        perms_str = getattr(profile, 'permissions', None) if profile else None
        if not perms_str:
            return False
        # Поддержка форматов: "read,write,delete" или JSON-массива
        return permission.strip().lower() in [p.strip().lower() for p in perms_str.replace(",", " ").split()]

    @staticmethod
    def require_permission(user: Any, permission: str) -> None:
        if not PermissionService.has_permission(user, permission):
            raise PermissionDeniedException(f"Отсутствует право: {permission}")