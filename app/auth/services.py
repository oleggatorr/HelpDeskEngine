from typing import Optional
from datetime import datetime, timedelta

from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, status
from sqlalchemy import select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    PasswordChangeRequest,
    UserResponse,
    UserProfileDTO,
    ProfileUpdateRequest,
    UserFilter,
    UserListResponse,
)
from app.auth.models import User, UserProfile
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _hash_password(password: str) -> str:
    """Хеширование пароля."""
    return pwd_context.hash(password)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля."""
    return pwd_context.verify(plain_password, hashed_password)


def _create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Создание access JWT токена."""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _create_refresh_token(user_id: int) -> str:
    """Создание refresh JWT токена."""
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_token(token: str) -> dict:
    """Декодирование JWT токена."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def _user_to_response(user: User) -> UserResponse:
    """Конвертация ORM-модели User в UserResponse."""
    return UserResponse(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
        profile=_profile_to_dto(user.profile) if user.profile else None,
    )


def _profile_to_dto(profile: UserProfile) -> Optional[UserProfileDTO]:
    """Конвертация ORM-модели UserProfile в UserProfileDTO."""
    if not profile:
        return None
    return UserProfileDTO(
        id=profile.id,
        user_id=profile.user_id,
        role=profile.role,
        position=profile.position,
        permissions=profile.permissions,
    )


# ==========================================
# AUTH SERVICE
# ==========================================

class AuthService:
    """Сервис аутентификации."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, request: LoginRequest) -> LoginResponse:
        """
        Вход: LoginRequest.
        Выход: LoginResponse.
        Комментарий: проверка учетных данных, выдача JWT.
        """
        result = await self.db.execute(
            select(User).where(User.login == request.login)
        )
        user = result.scalar_one_or_none()

        if not user or not _verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Пользователь деактивирован",
            )

        access_token = _create_access_token(user.id)
        refresh_token = _create_refresh_token(user.id)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def register(self, request: RegisterRequest) -> UserResponse:
        """
        Вход: RegisterRequest.
        Выход: UserResponse.
        Комментарий: создание нового пользователя.
        """
        # Проверка уникальности логина
        result = await self.db.execute(
            select(User).where(User.login == request.login)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким логином уже существует",
            )

        # Проверка уникальности email
        result = await self.db.execute(
            select(User).where(User.email == request.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email уже существует",
            )

        # Создание пользователя
        user = User(
            login=request.login,
            full_name=request.full_name,
            email=request.email,
            password_hash=_hash_password(request.password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Автоматическое создание профиля
        profile = UserProfile(user_id=user.id)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(user)

        return _user_to_response(user)

    async def refresh_token(self, refresh_token: str) -> LoginResponse:
        """
        Вход: refresh_token.
        Выход: LoginResponse.
        Комментарий: обновление access_token.
        """
        payload = _decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = int(payload["sub"])

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        access_token = _create_access_token(user.id)
        new_refresh_token = _create_refresh_token(user.id)

        return LoginResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    async def logout(self, token: str) -> bool:
        """
        Вход: token.
        Выход: bool.
        Комментарий: инвалидация токена (stateless — клиент удаляет токен).
        """
        _decode_token(token)
        # TODO: при необходимости добавить blacklist токенов в Redis/DB
        return True

    async def change_password(self, user_id: int, request: PasswordChangeRequest) -> bool:
        """
        Вход: user_id, PasswordChangeRequest.
        Выход: bool.
        Комментарий: смена пароля.
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        if not _verify_password(request.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный старый пароль",
            )

        await self.db.execute(
            sa_update(User)
            .where(User.id == user_id)
            .values(password_hash=_hash_password(request.new_password))
        )
        await self.db.commit()
        return True


# ==========================================
# USER SERVICE
# ==========================================

class UserService:
    """Сервис пользователей."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> Optional[UserResponse]:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.profile))  # ← Загружаем профиль одним запросом
        )
        user = result.scalar_one_or_none()
        return _user_to_response(user) if user else None

    async def get_by_login(self, login: str) -> Optional[UserResponse]:
        """
        Вход: login.
        Выход: Optional[UserResponse].
        Комментарий: поиск по логину.
        """
        result = await self.db.execute(
            select(User).where(User.login == login)
        )
        user = result.scalar_one_or_none()
        return _user_to_response(user) if user else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> UserListResponse:
        """
        Вход: skip, limit.
        Выход: UserListResponse.
        Комментарий: пагинированный список без фильтров.
        """
        return await self.list_filtered(skip=skip, limit=limit)

    async def list_filtered(
        self,
        filters: Optional[UserFilter] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> UserListResponse:
        """
        Вход: UserFilter, skip, limit.
        Выход: UserListResponse.
        Комментарий: пагинированный список с фильтрами по полям пользователя и профиля.
        """
        conditions = []

        if filters:
            # Фильтры по полям User
            if filters.login:
                conditions.append(User.login.ilike(f"%{filters.login}%"))
            if filters.full_name:
                conditions.append(User.full_name.ilike(f"%{filters.full_name}%"))
            if filters.email:
                conditions.append(User.email.ilike(f"%{filters.email}%"))
            if filters.is_active is not None:
                conditions.append(User.is_active == filters.is_active)

            # Фильтры по полям UserProfile (нужен JOIN)
            needs_profile_join = any([
                filters.role,
                filters.position,
                filters.permissions,
            ])

            if needs_profile_join:
                query_base = select(User).outerjoin(UserProfile, User.id == UserProfile.user_id)
                if filters.role:
                    conditions.append(UserProfile.role == filters.role)
                if filters.position:
                    conditions.append(UserProfile.position.ilike(f"%{filters.position}%"))
                if filters.permissions:
                    conditions.append(UserProfile.permissions.ilike(f"%{filters.permissions}%"))
            else:
                query_base = select(User)

            if conditions:
                from sqlalchemy import and_
                query_base = query_base.where(and_(*conditions))
        else:
            query_base = select(User)

        # Подсчёт общего количества (с теми же фильтрами)
        count_query = select(func.count()).select_from(query_base.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Пагинация
        query = query_base.order_by(User.id).distinct().offset(skip).limit(limit)
        result = await self.db.execute(query)
        users = result.scalars().all()

        return UserListResponse(
            users=[_user_to_response(u) for u in users],
            total=total,
        )

    async def get_profile(self, user_id: int) -> Optional[UserProfileDTO]:
        """
        Вход: user_id.
        Выход: Optional[UserProfileDTO].
        Комментарий: получение профиля.
        """
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        return _profile_to_dto(profile) if profile else None

    async def update_profile(self, user_id: int, request: ProfileUpdateRequest) -> UserProfileDTO:
        """
        Вход: user_id, ProfileUpdateRequest.
        Выход: UserProfileDTO.
        Комментарий: обновление роли, должности, допусков.
        """
        # Проверка наличия профиля
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            # Создание профиля если его нет
            profile = UserProfile(
                user_id=user_id,
                role=request.role,
                position=request.position,
                permissions=request.permissions,
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
        else:
            update_data = request.model_dump(exclude_unset=True)
            if update_data:
                await self.db.execute(
                    sa_update(UserProfile)
                    .where(UserProfile.user_id == user_id)
                    .values(**update_data)
                )
                await self.db.commit()
                await self.db.refresh(profile)

        return _profile_to_dto(profile)

    async def toggle_active(self, user_id: int) -> bool:
        """
        Вход: user_id.
        Выход: bool.
        Комментарий: активация/деактивация пользователя.
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return False

        await self.db.execute(
            sa_update(User)
            .where(User.id == user_id)
            .values(is_active=not user.is_active)
        )
        await self.db.commit()
        return True

    async def has_profile(self, user_id: int) -> bool:
        """
        Вход: user_id.
        Выход: bool.
        Комментарий: проверка наличия профиля у пользователя.
        """
        result = await self.db.execute(
            select(func.count(UserProfile.id)).where(UserProfile.user_id == user_id)
        )
        count = result.scalar_one()
        return count > 0
