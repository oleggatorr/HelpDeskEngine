from fastapi import HTTPException, status
from app.auth.models import User, UserRole


class PermissionDeniedException(HTTPException):
    """Исключение при отсутствии прав."""
    def __init__(self, detail: str = "Доступ запрещен"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class PermissionService:
    """Сервис проверки прав и ролей."""

    @staticmethod
    def has_role(user: User, role: UserRole) -> bool:
        """Проверка, есть ли у пользователя конкретная роль."""
        if not user:
            return False
        if not user.profile:
            return role == UserRole.USER
        user_role = user.profile.role
        return user_role == role

    @staticmethod
    def has_any_role(user: User, roles: list[UserRole]) -> bool:
        """Проверка, есть ли у пользователя одна из указанных ролей."""
        if not user:
            return UserRole.USER in roles
        user_role = user.profile.role if user.profile else UserRole.USER
        return user_role in roles

    @staticmethod
    def has_permission(user: User, permission: str) -> bool:
        """
        Проверка конкретного права.
        Формат прав в permissions: "ticket:create,ticket:edit,admin:delete"
        """
        if not user or not user.profile or not user.profile.permissions:
            return False
        
        permissions = user.profile.permissions.split(",")
        return permission in permissions

    @staticmethod
    def require_role(user: User, role: UserRole):
        """Выбросит исключение если нет роли."""
        if not PermissionService.has_role(user, role):
            raise PermissionDeniedException(
                f"Требуется роль: {role.value}"
            )

    @staticmethod
    def require_any_role(user: User, roles: list[UserRole]):
        """Выбросит исключение если нет ни одной из ролей."""
        if not PermissionService.has_any_role(user, roles):
            roles_str = ", ".join([r.value for r in roles])
            raise PermissionDeniedException(
                f"Требуется одна из ролей: {roles_str}"
            )

    @staticmethod
    def require_permission(user: User, permission: str):
        """Выбросит исключение если нет права."""
        if not PermissionService.has_permission(user, permission):
            raise PermissionDeniedException(
                f"Отсутствует право: {permission}"
            )
