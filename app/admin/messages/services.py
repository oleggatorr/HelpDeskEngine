from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.messages.services.chat_service import ChatService
from app.messages.services.message_service import MessageService
from app.messages.schemas.chat import (
    ChatCreate, ChatUpdate, ChatResponse, ChatListResponse, ChatFilter,
)
from app.messages.schemas.message import (
    MessageCreate, MessageResponse, MessageListResponse,
    MessageReadResponse, MessageAttachmentResponse,
)


class AdminMessageService:
    """Сервис админки для чатов и сообщений."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._chat_service = ChatService(db)
        self._message_service = MessageService(db)

    # --- Chats ---

    async def create_chat(self, request: ChatCreate, creator_id: int) -> ChatResponse:
        return await self._chat_service.create(request, creator_id)

    async def get_chat(self, chat_id: int, user_id: int) -> Optional[ChatResponse]:
        return await self._chat_service.get_by_id(chat_id, user_id)

    async def list_user_chats(self, user_id: int, skip: int = 0, limit: int = 100) -> ChatListResponse:
        return await self._chat_service.get_user_chats(user_id, skip, limit)

    async def list_all_chats(
        self,
        filters: Optional[ChatFilter] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> ChatListResponse:
        """Все чаты с фильтрами и сортировкой."""
        return await self._chat_service.list_all(filters, skip, limit)

    async def update_chat(self, chat_id: int, request: ChatUpdate) -> ChatResponse:
        return await self._chat_service.update(chat_id, request)

    async def delete_chat(self, chat_id: int) -> bool:
        return await self._chat_service.delete(chat_id)

    async def get_unread_count(self, chat_id: int, user_id: int) -> int:
        return await self._chat_service.get_unread_count(chat_id, user_id)

    # --- Messages ---

    async def create_message(self, request: MessageCreate, sender_id: int) -> MessageResponse:
        return await self._message_service.create(request, sender_id)

    async def get_message(self, message_id: int) -> Optional[MessageResponse]:
        return await self._message_service.get_by_id(message_id)

    async def list_chat_messages(
        self, chat_id: int, user_id: int, skip: int = 0, limit: int = 100
    ) -> MessageListResponse:
        return await self._message_service.get_chat_messages(chat_id, user_id, skip, limit)

    async def mark_read(self, message_id: int, user_id: int) -> MessageReadResponse:
        return await self._message_service.mark_as_read(message_id, user_id)

    async def mark_all_read(self, chat_id: int, user_id: int) -> int:
        return await self._message_service.mark_all_as_read(chat_id, user_id)

    async def delete_message(self, message_id: int) -> bool:
        return await self._message_service.delete(message_id)

    async def add_attachment(
        self, message_id: int, file_path: str, file_type: Optional[str] = None
    ) -> MessageAttachmentResponse:
        return await self._message_service.add_attachment(message_id, file_path, file_type)

    async def delete_attachment(self, attachment_id: int) -> bool:
        return await self._message_service.delete_attachment(attachment_id)

    async def get_attachments_by_message(self, message_id: int):
        return await self._message_service.get_attachments_by_message(message_id)

    async def get_attachment(self, attachment_id: int):
        return await self._message_service.get_attachment(attachment_id)
