from typing import Optional, List
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.messeges.models import Message, MessageAttachment, message_reads, Chat
from app.messeges.schemas import (
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    MessageReadResponse,
    MessageAttachmentResponse,
)


# ==========================================
# MESSAGE SERVICE
# ==========================================

class MessageService:
    """Сервис сообщений."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request: MessageCreate, sender_id: int) -> MessageResponse:
        """
        Вход: MessageCreate, sender_id.
        Выход: MessageResponse.
        Комментарий: создание сообщения (с вложениями или без).
        """
        message = Message(
            chat_id=request.chat_id,
            sender_id=sender_id,
            content=request.content,
        )
        self.db.add(message)
        await self.db.flush()

        # Вложения — сохраняем данные до коммита
        attachment_data = []
        if request.attachments:
            for att in request.attachments:
                attachment = MessageAttachment(
                    message_id=message.id,
                    file_path=att.file_path,
                    original_filename=att.original_filename,
                    file_type=att.file_type,
                )
                self.db.add(attachment)
                attachment_data.append({
                    "file_path": att.file_path,
                    "file_type": att.file_type,
                })

        await self.db.commit()

        # Загружаем sender отдельно (refresh не грузит отношения)
        if sender_id:
            from app.auth.models import User
            sender_result = await self.db.execute(
                select(User).where(User.id == sender_id)
            )
            sender = sender_result.scalar_one_or_none()
            sender_full_name = sender.full_name if sender else None
        else:
            sender_full_name = None

        await self.db.refresh(message)

        # ID вложений генерируются при insert — получаем их через запрос
        result = await self.db.execute(
            select(MessageAttachment.id, MessageAttachment.file_path, MessageAttachment.original_filename, MessageAttachment.file_type, MessageAttachment.uploaded_at)
            .where(MessageAttachment.message_id == message.id, MessageAttachment.is_deleted == False)
        )
        attachments = result.all()

        return MessageResponse(
            id=message.id,
            chat_id=message.chat_id,
            sender_id=message.sender_id,
            sender_full_name=sender_full_name,
            content=message.content,
            is_system=message.is_system,
            created_at=message.created_at,
            read_by_user_ids=[],
            attachments=[
                MessageAttachmentResponse(
                    id=a.id,
                    file_path=a.file_path,
                    original_filename=a.original_filename,
                    file_type=a.file_type,
                    uploaded_at=a.uploaded_at,
                )
                for a in attachments
            ],
        )

    async def get_by_id(self, message_id: int) -> Optional[MessageResponse]:
        """
        Вход: message_id.
        Выход: Optional[MessageResponse].
        Комментарий: получение сообщения по ID.
        """
        result = await self.db.execute(
            select(Message)
            .where(Message.id == message_id)
            .options(
                selectinload(Message.attachments),
                selectinload(Message.reads),
            )
        )
        message = result.scalar_one_or_none()
        if not message:
            return None

        return MessageResponse(
            id=message.id,
            chat_id=message.chat_id,
            sender_id=message.sender_id,
            sender_full_name=message.sender.full_name if message.sender else None,
            content=message.content,
            is_system=message.is_system,
            created_at=message.created_at,
            read_by_user_ids=[u.id for u in message.reads],
            attachments=[
                MessageAttachmentResponse(
                    id=a.id,
                    file_path=a.file_path,
                    original_filename=a.original_filename,
                    file_type=a.file_type,
                    uploaded_at=a.uploaded_at,
                )
                for a in message.attachments if not a.is_deleted
            ],
        )

    async def get_chat_messages(
        self,
        chat_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> MessageListResponse:
        """
        Вход: chat_id, user_id, skip, limit.
        Выход: MessageListResponse.
        Комментарий: сообщения чата с информацией о прочтении для пользователя.
        """
        # Проверяем анонимизацию чата
        chat_result = await self.db.execute(select(Chat).where(Chat.id == chat_id))
        chat = chat_result.scalar_one_or_none()
        is_anonymized = bool(chat and chat.is_anonymized)

        # Общее количество
        count_result = await self.db.execute(
            select(func.count(Message.id)).where(Message.chat_id == chat_id)
        )
        total = count_result.scalar_one()

        # Список сообщений
        result = await self.db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .options(
                selectinload(Message.attachments),
                selectinload(Message.reads),
                selectinload(Message.sender),
            )
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        messages = result.scalars().all()

        # Если чат анонимизирован — скрываем sender_id
        return MessageListResponse(
            messages=[
                MessageResponse(
                    id=m.id,
                    chat_id=m.chat_id,
                    sender_id=None if is_anonymized else m.sender_id,
                    sender_full_name=None if is_anonymized else (m.sender.full_name if m.sender else "Неизвестный"),
                    content=m.content,
                    is_system=m.is_system,
                    created_at=m.created_at,
                    read_by_user_ids=[u.id for u in m.reads],
                    attachments=[
                        MessageAttachmentResponse(
                            id=a.id,
                            file_path=a.file_path,
                            original_filename=a.original_filename,
                            file_type=a.file_type,
                            uploaded_at=a.uploaded_at,
                        )
                        for a in m.attachments if not a.is_deleted
                    ],
                )
                for m in messages
            ],
            total=total,
        )

    async def mark_as_read(self, message_id: int, user_id: int) -> MessageReadResponse:
        """
        Вход: message_id, user_id.
        Выход: MessageReadResponse.
        Комментарий: отметить сообщение как прочитанное.
        """
        # Проверяем, не отмечено ли уже
        result = await self.db.execute(
            select(message_reads).where(
                message_reads.c.message_id == message_id,
                message_reads.c.user_id == user_id,
            )
        )
        if result.fetchone():
            # Уже прочитано — возвращаем существующую запись
            result = await self.db.execute(
                select(Message).where(Message.id == message_id)
            )
            message = result.scalar_one()
            return MessageReadResponse(
                message_id=message_id,
                user_id=user_id,
                read_at=message.created_at,
            )

        # Вставляем запись
        await self.db.execute(
            message_reads.insert().values(
                message_id=message_id,
                user_id=user_id,
            )
        )
        await self.db.commit()

        result = await self.db.execute(select(Message).where(Message.id == message_id))
        message = result.scalar_one()

        return MessageReadResponse(
            message_id=message_id,
            user_id=user_id,
            read_at=datetime.utcnow(),
        )

    async def mark_all_as_read(self, chat_id: int, user_id: int) -> int:
        """
        Вход: chat_id, user_id.
        Выход: int.
        Комментарий: отметить все сообщения в чате как прочитанные.
        """
        # Получаем все сообщения чата
        result = await self.db.execute(
            select(Message.id).where(Message.chat_id == chat_id)
        )
        message_ids = [row[0] for row in result.all()]

        if not message_ids:
            return 0

        # Получаем уже прочитанные
        already_read = await self.db.execute(
            select(message_reads.c.message_id).where(
                message_reads.c.message_id.in_(message_ids),
                message_reads.c.user_id == user_id,
            )
        )
        already_read_ids = {row[0] for row in already_read.all()}

        # Вставляем только новые
        to_insert = [
            {"message_id": mid, "user_id": user_id}
            for mid in message_ids
            if mid not in already_read_ids
        ]

        if to_insert:
            await self.db.execute(message_reads.insert(), to_insert)
            await self.db.commit()

        return len(to_insert)

    async def delete(self, message_id: int) -> bool:
        """
        Вход: message_id.
        Выход: bool.
        Комментарий: удаление сообщения.
        """
        result = await self.db.execute(select(Message).where(Message.id == message_id))
        message = result.scalar_one_or_none()
        if not message:
            return False

        await self.db.delete(message)
        await self.db.commit()
        return True

    async def add_attachment(
        self,
        message_id: int,
        file_path: str,
        original_filename: Optional[str] = None,
        file_type: Optional[str] = None,
    ) -> MessageAttachmentResponse:
        """
        Вход: message_id, file_path, original_filename, file_type.
        Выход: MessageAttachmentResponse.
        Комментарий: добавление вложения к сообщению.
        """
        # Проверка существования сообщения
        result = await self.db.execute(select(Message).where(Message.id == message_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сообщение не найдено",
            )

        attachment = MessageAttachment(
            message_id=message_id,
            file_path=file_path,
            original_filename=original_filename,
            file_type=file_type,
        )
        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)

        return MessageAttachmentResponse(
            id=attachment.id,
            file_path=attachment.file_path,
            original_filename=attachment.original_filename,
            file_type=attachment.file_type,
            uploaded_at=attachment.uploaded_at,
        )

    async def delete_attachment(self, attachment_id: int) -> bool:
        """
        Вход: attachment_id.
        Выход: bool.
        Комментарий: мягкое удаление вложения (is_deleted = True).
        """
        result = await self.db.execute(
            select(MessageAttachment).where(MessageAttachment.id == attachment_id)
        )
        attachment = result.scalar_one_or_none()
        if not attachment or attachment.is_deleted:
            return False

        attachment.is_deleted = True
        await self.db.commit()
        return True

    async def get_attachments_by_message(self, message_id: int) -> List[MessageAttachmentResponse]:
        """
        Вход: message_id.
        Выход: List[MessageAttachmentResponse].
        Комментарий: все вложения сообщения.
        """
        result = await self.db.execute(
            select(MessageAttachment)
            .where(MessageAttachment.message_id == message_id, MessageAttachment.is_deleted == False)
            .order_by(MessageAttachment.uploaded_at.asc())
        )
        attachments = result.scalars().all()
        return [
            MessageAttachmentResponse(
                id=a.id,
                file_path=a.file_path,
                original_filename=a.original_filename,
                file_type=a.file_type,
                uploaded_at=a.uploaded_at,
            )
            for a in attachments
        ]

    async def get_attachment(self, attachment_id: int) -> Optional[MessageAttachmentResponse]:
        """
        Вход: attachment_id.
        Выход: Optional[MessageAttachmentResponse].
        Комментарий: вложение по ID.
        """
        result = await self.db.execute(
            select(MessageAttachment).where(MessageAttachment.id == attachment_id, MessageAttachment.is_deleted == False)
        )
        attachment = result.scalar_one_or_none()
        if not attachment:
            return None

        return MessageAttachmentResponse(
            id=attachment.id,
            file_path=attachment.file_path,
            original_filename=attachment.original_filename,
            file_type=attachment.file_type,
            uploaded_at=attachment.uploaded_at,
        )

