from typing import Optional, List
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select, func, delete
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
        filters = ChatFilter(participant_id=user_id)
        return await self.list_all(filters=filters, skip=skip, limit=limit)

    async def list_all(
        self,
        filters: Optional[ChatFilter] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> ChatListResponse:
        """
        Вход: ChatFilter, skip, limit.
        Выход: ChatListResponse.
        Комментарий: все чаты с фильтрами и сортировкой.
        """
        conditions = []
        needs_participant_join = False

        if filters:
            if filters.participant_id is not None:
                needs_participant_join = True
                conditions.append(chat_participants.c.user_id == filters.participant_id)
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

        # Базовый запрос
        if needs_participant_join:
            query_base = select(Chat).join(chat_participants)
        else:
            query_base = select(Chat)

        if conditions:
            from sqlalchemy import and_
            query_base = query_base.where(and_(*conditions))

        # Подсчёт
        count_query = select(func.count()).select_from(query_base.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Сортировка
        sort_col = getattr(Chat, filters.sort_by) if filters and filters.sort_by else Chat.updated_at
        order_fn = sort_col.asc if (filters and filters.sort_order == "asc") else sort_col.desc

        # Пагинация
        result = await self.db.execute(
            query_base
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

    async def update(self, chat_id: int, request: ChatUpdate, remover_id: Optional[int] = None) -> ChatResponse:
        """
        Вход: chat_id, ChatUpdate, remover_id (для защиты от самоудаления).
        Выход: ChatResponse.
        Комментарий: добавление/удаление участников.
        """
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id).options(selectinload(Chat.participants))
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Чат не найден",
            )

        # Обновление названия
        if request.name is not None:
            chat.name = request.name

        # Обновление статуса архива
        if request.is_archived is not None:
            chat.is_archived = int(request.is_archived)

        # Обновление статуса закрытия
        if request.is_closed is not None:
            chat.is_closed = int(request.is_closed)

        # Обновление статуса анонимизации
        if request.is_anonymized is not None:
            chat.is_anonymized = int(request.is_anonymized)

        # Добавление участников
        if request.add_participant_ids:
            result = await self.db.execute(
                select(User).where(User.id.in_(request.add_participant_ids))
            )
            users_to_add = result.scalars().all()
            existing_ids = {u.id for u in chat.participants}
            for user in users_to_add:
                if user.id not in existing_ids:
                    chat.participants.append(user)

        # Удаление участников — защита от самоудаления
        if request.remove_participant_ids:
            if remover_id and remover_id in request.remove_participant_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Нельзя удалить себя из чата. Используйте «Покинуть чат».",
                )
            chat.participants = [
                p for p in chat.participants
                if p.id not in request.remove_participant_ids
            ]

        # Сохраняем ID до коммита
        participant_ids = [] if chat.is_anonymized else [p.id for p in chat.participants]

        await self.db.commit()
        await self.db.refresh(chat)

        # Если участников не осталось — удаляем чат каскадно (вложения мягко)
        if not chat.participants:
            await self._delete_chat_with_soft_attachments(chat_id)
            # Возвращаем response с флагом удаления через participant_ids = []
            return ChatResponse(
                id=chat.id,
                name=chat.name,
                document_id=chat.document_id,
                is_archived=bool(chat.is_archived),
                is_closed=bool(chat.is_closed),
                is_anonymized=bool(chat.is_anonymized),
                participant_ids=[],
                created_at=chat.created_at,
                updated_at=chat.updated_at,
            )

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

    # ==========================================
    # HELPERS
    # ==========================================
