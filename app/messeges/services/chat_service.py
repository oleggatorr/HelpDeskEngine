from typing import Optional, List
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select, func, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.messeges.models import Chat, Message, MessageAttachment, chat_participants, message_reads
from app.messeges.schemas import (
    ChatCreate,
    ChatUpdate,
    ChatResponse,
    ChatListResponse,
    ChatFilter,
)
from app.auth.models import User
from app.reports.documents.models import Document


# ==========================================
# CHAT SERVICE
# ==========================================

class ChatService:
    """Сервис чатов."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request: ChatCreate, creator_id: int) -> ChatResponse:
        """
        Вход: ChatCreate, creator_id.
        Выход: ChatResponse.
        Комментарий: создание чата с участниками.
        """
        # Проверяем, что creator_id в списке участников
        participant_ids = list(set(request.participant_ids))
        if creator_id not in participant_ids:
            participant_ids.append(creator_id)

        # Проверяем существование участников
        result = await self.db.execute(
            select(User).where(User.id.in_(participant_ids))
        )
        participants = result.scalars().all()
        existing_ids = {p.id for p in participants}
        missing = set(participant_ids) - existing_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Пользователи не найдены: {missing}",
            )

        chat = Chat(
            name=request.name,
            document_id=request.document_id if request.document_id else None,
        )
        chat.participants = participants
        self.db.add(chat)

        # Сохраняем ID до коммита (после commit объекты expire)
        participant_ids = [p.id for p in participants]

        await self.db.commit()
        await self.db.refresh(chat)

        return ChatResponse(
            id=chat.id,
            name=chat.name,
            document_id=chat.document_id,
            is_archived=bool(chat.is_archived),
            is_closed=bool(chat.is_closed),
            is_anonymized=bool(chat.is_anonymized),
            participant_ids=participant_ids,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    async def get_by_id(self, chat_id: int, user_id: int) -> Optional[ChatResponse]:
        """
        Вход: chat_id, user_id.
        Выход: Optional[ChatResponse].
        Комментарий: получение чата по ID с информацией о непрочитанных.
        """
        result = await self.db.execute(
            select(Chat)
            .where(Chat.id == chat_id)
            .options(selectinload(Chat.participants))
        )
        chat = result.scalar_one_or_none()
        if not chat:
            return None

        if user_id not in [p.id for p in chat.participants]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к чату",
            )

        return ChatResponse(
            id=chat.id,
            name=chat.name,
            document_id=chat.document_id,
            is_archived=bool(chat.is_archived),
            is_closed=bool(chat.is_closed),
            is_anonymized=bool(chat.is_anonymized),
            participant_ids=[] if chat.is_anonymized else [p.id for p in chat.participants],
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    async def get_user_chats(self, user_id: int, skip: int = 0, limit: int = 100) -> ChatListResponse:
        """
        Вход: user_id, skip, limit.
        Выход: ChatListResponse.
        Комментарий: все чаты пользователя (обёртка над list_all).
        """
        filters = ChatFilter(participant_id=user_id, creator_id=user_id)
        return await self.list_all(filters=filters, skip=skip, limit=limit)

    async def list_all(
        self,
        filters: Optional[ChatFilter] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> ChatListResponse:
        conditions = []
        print( filters)
        if filters:
            uid = filters.participant_id

            # 🔒 1. ЖЁСТКОЕ УСЛОВИЕ: пользователь ОБЯЗАН быть участником чата
            conditions.append(Chat.participants.any(id=uid))

            # 🎛️ 2. Комбинируемые роли (объединяются через OR)
            scope_conditions = []
            
            if filters.include_creator:
                scope_conditions.append(Chat.document.has(created_by=uid))
                
            if filters.include_assigned:
                scope_conditions.append(Chat.document.has(assigned_to=uid))
                
            if filters.include_other:
                # Не создатель И не назначен
                not_creator = ~Chat.document.has(created_by=uid)
                not_assigned = ~Chat.document.has(assigned_to=uid)
                scope_conditions.append(not_creator & not_assigned)

            if scope_conditions:
                conditions.append(or_(*scope_conditions))

            # 📋 3. Остальные фильтры (всегда AND)
            if filters.document_id is not None:
                conditions.append(Chat.document_id == filters.document_id)
            if filters.name:
                conditions.append(Chat.name.ilike(f"%{filters.name}%"))
            if filters.is_archived is not None:
                conditions.append(Chat.is_archived == int(filters.is_archived))
            if filters.is_closed is not None:
                conditions.append(Chat.is_closed == int(filters.is_closed))
            if filters.is_anonymized is not None:
                conditions.append(Chat.is_anonymized == int(filters.is_anonymized))
            if filters.created_from is not None:
                conditions.append(Chat.created_at >= filters.created_from)
            if filters.created_to is not None:
                conditions.append(Chat.created_at <= filters.created_to)

        # 📦 Базовый запрос + DISTINCT (гарантия уникальности)
        stmt = select(Chat).distinct()
        if conditions:
            stmt = stmt.where(and_(*conditions))

        # 🔢 Подсчёт total (зеркально повторяет WHERE основного запроса)
        count_stmt = select(func.count(Chat.id.distinct()))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar_one()

        # 📐 Сортировка
        sort_col = getattr(Chat, filters.sort_by) if filters and hasattr(Chat, filters.sort_by) else Chat.updated_at
        order_fn = sort_col.asc if (filters and filters.sort_order == "asc") else sort_col.desc

        # 📥 Пагинация + eager-load участников
        result = await self.db.execute(
            stmt
            .options(selectinload(Chat.participants))
            .order_by(order_fn())
            .offset(skip)
            .limit(limit)
        )
        chats = result.scalars().all()

        return ChatListResponse(
            chats=[
                ChatResponse(
                    id=c.id,
                    name=c.name,
                    document_id=c.document_id,
                    is_archived=bool(c.is_archived),
                    is_closed=bool(c.is_closed),
                    is_anonymized=bool(c.is_anonymized),
                    participant_ids=[] if c.is_anonymized else [p.id for p in c.participants],
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in chats
            ],
            total=total,
        )

    async def _delete_chat_with_soft_attachments(self, chat_id: int):
        """Мягкое удаление вложений сообщений + каскадное удаление чата."""
        from app.messeges.models import MessageAttachment, Message
        from sqlalchemy import select

        # Получаем все сообщения чата
        result = await self.db.execute(
            select(Message.id).where(Message.chat_id == chat_id)
        )
        message_ids = [row[0] for row in result.all()]

        if message_ids:
            # Мягкое удаление всех вложений
            await self.db.execute(
                MessageAttachment.__table__.update()
                .where(MessageAttachment.message_id.in_(message_ids))
                .values(is_deleted=True)
            )

        await self.db.commit()

        # Каскадное удаление чата (сообщения, участники удалятся по cascade)
        result = await self.db.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if chat:
            await self.db.delete(chat)
            await self.db.commit()

    async def delete(self, chat_id: int) -> bool:
        """
        Вход: chat_id.
        Выход: bool.
        Комментарий: удаление чата.
        """
        result = await self.db.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if not chat:
            return False

        await self.db.delete(chat)
        await self.db.commit()
        return True

    async def get_unread_count(self, chat_id: int, user_id: int) -> int:
        """
        Вход: chat_id, user_id.
        Выход: int.
        Комментарий: количество непрочитанных сообщений для пользователя.
        """
        # Все сообщения в чате минус прочитанные данным пользователем
        subq = (
            select(func.count(Message.id))
            .where(Message.chat_id == chat_id)
            .scalar_subquery()
        )
        read_subq = (
            select(func.count(message_reads.c.message_id))
            .where(
                message_reads.c.message_id.in_(
                    select(Message.id).where(Message.chat_id == chat_id)
                )
            )
            .where(message_reads.c.user_id == user_id)
            .scalar_subquery()
        )
        result = await self.db.execute(select(subq - read_subq))
        return result.scalar_one() or 0



    async def update(self, chat_id: int, request: ChatUpdate, **kwargs) -> Optional[ChatResponse]:
        """
        Вход: chat_id, ChatUpdate.
        Выход: Optional[ChatResponse].
        Комментарий: обновление чата (поля + участники).
        """
        # Получаем чат с участниками
        result = await self.db.execute(
            select(Chat)
            .where(Chat.id == chat_id)
            .options(selectinload(Chat.participants))
        )
        chat = result.scalar_one_or_none()
        if not chat:
            return None
        
        update_data = request.model_dump(exclude_unset=True)
        
        # 🔹 Обработка добавления участников (через ассоциативную таблицу)
        if "add_participant_ids" in update_data and update_data["add_participant_ids"]:
            for user_id in update_data["add_participant_ids"]:
                # Проверяем существование пользователя
                user_result = await self.db.execute(select(User).where(User.id == user_id))
                if not user_result.scalar_one_or_none():
                    continue  # Пропускаем несуществующих, или можно raise HTTPException
                
                # Проверяем, нет ли уже такого участника
                exists = await self.db.execute(
                    select(chat_participants.c.user_id).where(
                        chat_participants.c.chat_id == chat_id,
                        chat_participants.c.user_id == user_id
                    )
                )
                if not exists.scalar_one_or_none():
                    # Добавляем в ассоциативную таблицу
                    stmt = chat_participants.insert().values(chat_id=chat_id, user_id=user_id)
                    await self.db.execute(stmt)
            update_data.pop("add_participant_ids")
        
        # 🔹 Обработка удаления участников
        if "remove_participant_ids" in update_data and update_data["remove_participant_ids"]:
            for user_id in update_data["remove_participant_ids"]:
                stmt = chat_participants.delete().where(
                    chat_participants.c.chat_id == chat_id,
                    chat_participants.c.user_id == user_id
                )
                await self.db.execute(stmt)
            update_data.pop("remove_participant_ids")
        
        # 🔹 Обновление остальных полей модели
        for field, value in update_data.items():
            if value is not None and hasattr(chat, field):
                setattr(chat, field, value)
        
        # Обновляем timestamp
        chat.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(chat)
        
        # Возвращаем ChatResponse в том же формате, что и другие методы
        return ChatResponse(
            id=chat.id,
            name=chat.name,
            document_id=chat.document_id,
            is_archived=bool(chat.is_archived),
            is_closed=bool(chat.is_closed),
            is_anonymized=bool(chat.is_anonymized),
            participant_ids=[] if chat.is_anonymized else [p.id for p in chat.participants],
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )
    # ==========================================
    # HELPERS
    # ==========================================


