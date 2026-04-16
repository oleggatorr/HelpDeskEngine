from fastapi import HTTPException, status
from app.auth.models import User, UserRole
from app.auth.services import UserService


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
    def has_role(user, role: UserRole) -> bool:
        """
        Проверка, есть ли у пользователя конкретная роль.
        Работает и с SQLAlchemy-моделью, и с Pydantic-схемой.
        """
        if not user:
            return False
        
        # Получаем профиль: для модели - атрибут, для схемы - поле
        profile = getattr(user, 'profile', None)
        if not profile:
            return False
        
        # Получаем роль из профиля
        user_role = getattr(profile, 'role', None)
        if not user_role:
            return False
        
        # Сравниваем: если роль — Enum, берём .value, иначе сравниваем как строку
        role_value = user_role.value if hasattr(user_role, 'value') else str(user_role)
        target_value = role.value if hasattr(role, 'value') else str(role)
        
        return role_value == target_value

    @staticmethod
    def has_any_role(user, roles: list[UserRole]) -> bool:
        """Проверка, есть ли у пользователя одна из указанных ролей."""
        if not user:
            return False
        return any(PermissionService.has_role(user, r) for r in roles)

    @staticmethod
    def require_role(user, role: UserRole):
        """Выбросит 403 если нет роли."""
        from fastapi import HTTPException, status
        if not PermissionService.has_role(user, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется роль: {role.value}"
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
