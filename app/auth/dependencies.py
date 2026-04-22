# app/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from app.auth.models import User, UserRole
from app.auth.services import PermissionService
from app.core.dependencies import get_current_user

def require_roles(*allowed_roles: UserRole):
    """
    Декоратор для защиты роутов: разрешает доступ только указанным ролям.
    Использование: @router.get("/admin", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QE))])
    """
    async def checker(current_user: User = Depends(get_current_user)):
        if not PermissionService.has_any_role(current_user, list(allowed_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ запрещён. Требуется одна из ролей: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return checker