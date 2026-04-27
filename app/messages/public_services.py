from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.messages.services.chat_service import ChatService
from app.messages.services.message_service import MessageService
from app.messages.schemas import ChatResponse


class PublicChatService:
    """Публичный слой чатов."""

    def __init__(self, db: AsyncSession):
        self._service = ChatService(db)
        self.db = db
        self._message_service = MessageService(db)

    async def _send_system_message(self, chat_id: int, content: str):
        """Отправить системное сообщение в чат."""
        from app.messages.models import Message
        msg = Message(
            chat_id=chat_id,
            sender_id=None,
            content=content,
            is_system=True,
        )
        self.db.add(msg)
        await self.db.commit()

    async def create(self, *args, **kwargs):
        return await self._service.create(*args, **kwargs)

    async def get_by_id(self, *args, **kwargs):
        return await self._service.get_by_id(*args, **kwargs)

    async def get_user_chats(self, *args, **kwargs):
        return await self._service.get_user_chats(*args, **kwargs)

    async def get_user_chats_with_unread(self, user_id: int, skip: int = 0, limit: int = 100):
        """Список чатов пользователя с количеством непрочитанных."""
        chats_result = await self._service.get_user_chats(user_id=user_id, skip=skip, limit=limit)
        chats_with_unread: List[ChatResponse] = []
        for chat in chats_result.chats:
            unread = await self._service.get_unread_count(chat.id, user_id=user_id)
            chats_with_unread.append(ChatResponse(
                id=chat.id,
                name=chat.name,
                document_id=chat.document_id,
                is_archived=chat.is_archived,
                is_closed=chat.is_closed,
                is_anonymized=chat.is_anonymized,
                participant_ids=[] if chat.is_anonymized else chat.participant_ids,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                unread_count=unread,
            ))
        from app.messages.schemas import ChatListResponse
        return ChatListResponse(chats=chats_with_unread, total=chats_result.total)

    async def list_all(self, *args, **kwargs):
        return await self._service.list_all(*args, **kwargs)

    async def update(self, chat_id: int, request, **kwargs):
        """Обновить чат с отправкой системных сообщений о участниках."""

        # Отправляем системные сообщения о добавлении участников ДО обновления
        if hasattr(request, 'add_participant_ids') and request.add_participant_ids:
            for uid in request.add_participant_ids:
                await self._send_system_message(chat_id, f"➕ Пользователь ID {uid} добавлен в чат")

        # Отправляем системные сообщения об удалении участников
        if hasattr(request, 'remove_participant_ids') and request.remove_participant_ids:
            for uid in request.remove_participant_ids:
                await self._send_system_message(chat_id, f"➖ Пользователь ID {uid} покинул чат")

        return await self._service.update(chat_id, request, **kwargs)

    async def delete(self, *args, **kwargs):
        return await self._service.delete(*args, **kwargs)

    async def get_unread_count(self, *args, **kwargs):
        return await self._service.get_unread_count(*args, **kwargs)

    # === Архив ===
    async def archive(self, chat_id: int, user_id: int):
        """Архивировать чат."""
        from app.messages.schemas import ChatUpdate
        result = await self.update(chat_id, ChatUpdate(is_archived=True))
        await self._send_system_message(chat_id, "📦 Чат архивирован")
        return result

    async def unarchive(self, chat_id: int, user_id: int):
        """Разархивировать чат."""
        from app.messages.schemas import ChatUpdate
        result = await self.update(chat_id, ChatUpdate(is_archived=False))
        await self._send_system_message(chat_id, "📦 Чат разархивирован")
        return result

    # === Закрытие/Открытие ===
    async def close(self, chat_id: int, user_id: int):
        """Закрыть чат."""
        from app.messages.schemas import ChatUpdate
        result = await self.update(chat_id, ChatUpdate(is_closed=True))
        await self._send_system_message(chat_id, "🔒 Чат закрыт")
        return result

    async def open(self, chat_id: int, user_id: int):
        """Открыть чат."""
        from app.messages.schemas import ChatUpdate
        result = await self.update(chat_id, ChatUpdate(is_closed=False))
        await self._send_system_message(chat_id, "🔓 Чат открыт")
        return result

    # === Анонимизация ===
    async def anonymize(self, chat_id: int, user_id: int):
        """Анонимизировать чат."""
        from app.messages.schemas import ChatUpdate
        result = await self.update(chat_id, ChatUpdate(is_anonymized=True))
        await self._send_system_message(chat_id, "👤 Чат анонимизирован")
        return result

    async def deanonymize(self, chat_id: int, user_id: int):
        """Деанонимизировать чат."""
        from app.messages.schemas import ChatUpdate
        result = await self.update(chat_id, ChatUpdate(is_anonymized=False))
        await self._send_system_message(chat_id, "👤 Чат деанонимизирован")
        return result

    async def get_document_id(self, chat_id: int) -> Optional[int]:
        """Получить ID документа, привязанного к чату."""
        from app.messages.models import Chat
        result = await self.db.execute(
            select(Chat.document_id).where(Chat.id == chat_id)
        )
        return result.scalar_one_or_none()

    async def get_chat_id_by_document(self, document_id: int) -> Optional[int]:
        """Получить ID чата, привязанного к документу."""
        from app.messages.models import Chat
        result = await self.db.execute(
            select(Chat.id).where(Chat.document_id == document_id)
        )
        return result.scalar_one_or_none()

    async def add_participant_by_document(self, document_id: int, user_id: int) -> bool:
        """Добавить пользователя в чат, привязанный к документу.
        Возвращает True если участник добавлен, False если чат не найден.
        Выбрасывает ValueError если пользователь уже участник.
        """
        chat_id = await self.get_chat_id_by_document(document_id)
        if not chat_id:
            return False

        # Проверяем, является ли пользователь уже участником (напрямую через БД)
        from app.messages.models import chat_participants
        result = await self.db.execute(
            select(chat_participants.c.user_id).where(
                chat_participants.c.chat_id == chat_id,
                chat_participants.c.user_id == user_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise ValueError(f"Пользователь ID {user_id} уже является участником чата")

        from app.messages.schemas import ChatUpdate
        await self.update(chat_id, ChatUpdate(add_participant_ids=[user_id]))
        return True


class PublicMessageService:
    """Публичный слой сообщений."""

    def __init__(self, db: AsyncSession):
        self._service = MessageService(db)

    async def create(self, *args, **kwargs):
        return await self._service.create(*args, **kwargs)

    async def get_by_id(self, *args, **kwargs):
        return await self._service.get_by_id(*args, **kwargs)

    async def get_chat_messages(self, *args, **kwargs):
        return await self._service.get_chat_messages(*args, **kwargs)

    async def mark_as_read(self, *args, **kwargs):
        return await self._service.mark_as_read(*args, **kwargs)

    async def mark_all_as_read(self, *args, **kwargs):
        return await self._service.mark_all_as_read(*args, **kwargs)

    async def delete(self, *args, **kwargs):
        return await self._service.delete(*args, **kwargs)

    async def add_attachment(self, *args, **kwargs):
        return await self._service.add_attachment(*args, **kwargs)

    async def delete_attachment(self, *args, **kwargs):
        return await self._service.delete_attachment(*args, **kwargs)

    async def get_attachments_by_message(self, *args, **kwargs):
        return await self._service.get_attachments_by_message(*args, **kwargs)

    async def get_attachment(self, *args, **kwargs):
        return await self._service.get_attachment(*args, **kwargs)

    async def send_system_message(self, chat_id: int, content: str) -> Optional[int]:
        """Отправить системное сообщение в чат. Возвращает ID сообщения."""
        from app.messages.models import Message
        msg = Message(
            chat_id=chat_id,
            sender_id=None,
            content=content,
            is_system=True,
        )
        self._service.db.add(msg)
        await self._service.db.commit()
        await self._service.db.refresh(msg)
        return msg.id
