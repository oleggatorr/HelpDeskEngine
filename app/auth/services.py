from typing import Optional
from datetime import datetime, timedelta
import logging

from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, status
from sqlalchemy import select, func, update as sa_update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.schemas import (
    LoginRequest, LoginResponse, RegisterRequest, PasswordChangeRequest,
    UserResponse, UserProfileDTO, ProfileUpdateRequest, UserFilter, UserListResponse
)
from app.auth.models import User, UserProfile
from app.core.config import settings

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _hash_password(password: str) -> str:
    return pwd_context.hash(password)

def _verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def _create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def _create_refresh_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

def _profile_to_dto(profile: UserProfile) -> Optional[UserProfileDTO]:
    if not profile:
        return None
    return UserProfileDTO(
        id=profile.id,
        user_id=profile.user_id,
        role=profile.role,
        position=profile.position,
        permissions=profile.permissions,
        department_id=profile.department_id,
        department=profile.department,  # ✅ Pydantic распарсит благодаря from_attributes=True
    )

def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        login=user.login,
        full_name=user.full_name,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
        profile=_profile_to_dto(user.profile) if user.profile else None,
    )

# ==========================================
# AUTH SERVICE
# ==========================================

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, request: LoginRequest) -> LoginResponse:
        
        result = await self.db.execute(
            select(User).where(User.login == request.login)
        )
        user = result.scalar_one_or_none()
        
        if not user or not _verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь деактивирован")

        return LoginResponse(
            access_token=_create_access_token(user.id),
            refresh_token=_create_refresh_token(user.id),
        )

    async def register(self, request: RegisterRequest) -> UserResponse:
        # Проверки уникальности
        for field, error_msg in [
            (User.login, "Логин занят"), 
            (User.email, "Email занят")
        ]:
            res = await self.db.execute(select(User).where(field == getattr(request, field.name.split('.')[-1])))
            if res.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)

        user = User(
            login=request.login, full_name=request.full_name, email=request.email,
            password_hash=_hash_password(request.password),
            is_active=True
        )
        self.db.add(user)
        await self.db.flush()  # ✅ Получаем user.id до коммита
        
        profile = UserProfile(user_id=user.id)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(user, attribute_names=["profile"])
        
        return _user_to_response(user)

    async def refresh_token(self, refresh_token: str) -> LoginResponse:
        payload = _decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        user = (await self.db.execute(select(User).where(User.id == int(payload["sub"])))).scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

        return LoginResponse(
            access_token=_create_access_token(user.id),
            refresh_token=_create_refresh_token(user.id),
        )

    async def logout(self, token: str) -> bool:
        _decode_token(token)
        return True

    async def change_password(self, user_id: int, request: PasswordChangeRequest) -> bool:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        if not _verify_password(request.old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Неверный старый пароль")

        await self.db.execute(
            sa_update(User).where(User.id == user_id).values(password_hash=_hash_password(request.new_password))
        )
        await self.db.commit()
        return True


# ==========================================
# USER SERVICE
# ==========================================

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> Optional[UserResponse]:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                # 🔥 Правильная цепочка: User → UserProfile → Department
                selectinload(User.profile)
                .selectinload(UserProfile.department)  # ← UserProfile, не Profile!
            )
        )
        
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()
        
        if not user:
            return None
            
        return _user_to_response(user)

    async def list_filtered(
        self, filters: Optional[UserFilter] = None, skip: int = 0, limit: int = 100
    ) -> UserListResponse:
        conditions = []
        needs_profile_join = False

        if filters:
            if filters.login: conditions.append(User.login.ilike(f"%{filters.login}%"))
            if filters.full_name: conditions.append(User.full_name.ilike(f"%{filters.full_name}%"))
            if filters.email: conditions.append(User.email.ilike(f"%{filters.email}%"))
            if filters.is_active is not None: conditions.append(User.is_active == filters.is_active)

            if filters.department_id:
                needs_profile_join = True
                conditions.append(UserProfile.department_id == filters.department_id)
            if filters.role:
                needs_profile_join = True
                conditions.append(UserProfile.role == filters.role)
            if filters.position:
                needs_profile_join = True
                conditions.append(UserProfile.position.ilike(f"%{filters.position}%"))
            if filters.permissions:
                needs_profile_join = True
                conditions.append(UserProfile.permissions.ilike(f"%{filters.permissions}%"))

        # 🔹 Формируем базовый запрос
        base_query = select(User)
        if needs_profile_join:
            base_query = base_query.outerjoin(UserProfile, User.id == UserProfile.user_id)
        if conditions:
            base_query = base_query.where(and_(*conditions))

        # 🔹 Корректный подсчёт total (без subquery и с учётом distinct)
        count_query = select(func.count(User.id.distinct())).select_from(User)
        if needs_profile_join:
            count_query = count_query.outerjoin(UserProfile, User.id == UserProfile.user_id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
            
        total = (await self.db.execute(count_query)).scalar_one()

        # 🔹 Пагинация + загрузка профиля
        query = base_query.order_by(User.id).distinct().offset(skip).limit(limit)
        query = query.options(selectinload(User.profile))
        users = (await self.db.execute(query)).scalars().all()

        return UserListResponse(users=[_user_to_response(u) for u in users], total=total)

    async def get_profile(self, user_id: int) -> Optional[UserProfileDTO]:
        res = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        return _profile_to_dto(res.scalar_one_or_none())

    async def update_profile(self, user_id: int, request: ProfileUpdateRequest) -> UserProfileDTO:
        profile = (await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalar_one_or_none()
        
        update_data = request.model_dump(exclude_unset=True)
        if not profile:
            profile = UserProfile(user_id=user_id, **update_data)
            self.db.add(profile)
        elif update_data:
            await self.db.execute(
                sa_update(UserProfile).where(UserProfile.user_id == user_id).values(**update_data)
            )
            
        await self.db.commit()
        await self.db.refresh(profile)
        return _profile_to_dto(profile)

    async def toggle_active(self, user_id: int) -> bool:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user: return False
        await self.db.execute(sa_update(User).where(User.id == user_id).values(is_active=not user.is_active))
        await self.db.commit()
        return True

    async def has_profile(self, user_id: int) -> bool:
        res = await self.db.execute(select(func.count(UserProfile.id)).where(UserProfile.user_id == user_id))
        return res.scalar_one() > 0