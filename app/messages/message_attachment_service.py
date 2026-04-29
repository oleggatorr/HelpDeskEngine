# app\messages\message_attachment_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.storage.file_storage import FileStorage
from app.messages.models import MessageAttachment
from app.messages.schemas import MessageAttachmentCreate

from loguru import logger

class MessageAttachmentService:

    def __init__(self, db: AsyncSession, storage: FileStorage):
        self.db = db
        self.storage = storage
        logger.debug("MessageAttachmentService initialized")

    async def upload(
        self,
        message_id: int,
        content: bytes,
        filename: str,
        user_id: int,
        file_type: str | None = None,
    ) -> MessageAttachment:

        # 1. сохраняем файл
        path = self.storage.save(content, filename)

        try:
            
            # 2. создаём ORM модель (ВАЖНО: не Pydantic)
            attachment = MessageAttachment(
                message_id=message_id,
                file_path=path,
                original_filename=filename,
                file_type=file_type,
                uploaded_by=user_id,
            )
            print(attachment)

            self.db.add(attachment)
            await self.db.flush()

            logger.info(
                f"Attachment uploaded: message_id={message_id}, file={filename}"
            )

            return attachment

        except Exception as e:
            logger.error(f"Upload failed, removing file: {path}")

            self.storage.delete(path)
            raise