from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload  # 🔥 Импортируем

from app.core.database import get_db
from app.core.config import settings
from app.auth.models import User, UserProfile, UserRole
from app.auth.permission_service import PermissionService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Получение текущего пользователя из JWT-токена с загруженным профилем."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
        )

    # 🔥 Ключевое: загружаем profile сразу через selectinload
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile))  # <-- загружаем профиль одним запросом
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Проверка, что пользователь — администратор."""
    # 🔥 profile уже загружен благодаря selectinload в get_current_user
    if not current_user.profile or current_user.profile.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора",
        )
    return current_user


def require_roles(*allowed_roles: UserRole):
    """Dependency-фабрика для проверки ролей."""
    async def checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        # 🔥 PermissionService.has_any_role() теперь работает синхронно,
        # потому что current_user.profile уже в памяти
        if not PermissionService.has_any_role(current_user, list(allowed_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ запрещён. Требуется одна из ролей: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return checker