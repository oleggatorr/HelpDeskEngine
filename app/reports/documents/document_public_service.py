from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.reports.documents.document_service import DocumentService


class PublicDocumentService:
    """Публичный слой документов."""

    def __init__(self, db: AsyncSession):
        self._service = DocumentService(db)

    async def create(self, *args, **kwargs):
        return await self._service.create(*args, **kwargs)

    async def get_by_id(self, *args, **kwargs):
        return await self._service.get_by_id(*args, **kwargs)

    async def get_by_track_id(self, *args, **kwargs):
        return await self._service.get_by_track_id(*args, **kwargs)

    async def get_all(self, *args, **kwargs):
        return await self._service.get_all(*args, **kwargs)

    async def list_filtered(self, *args, **kwargs):
        return await self._service.list_filtered(*args, **kwargs)

    async def update_stage(self, *args, **kwargs):
        return await self._service.update_stage(*args, **kwargs)

    async def update(self, doc_id: int, request, user_id: int = None, **kwargs):
        """Обновить документ с жёсткой проверкой блокировки."""
        from fastapi import HTTPException, status
        from app.reports.documents.models import Document
        from sqlalchemy import select
        # 🔒 Проверяем блокировку, если явно не разрешено её обходить

        lock_result = await self._service.db.execute(select(Document.is_locked).where(Document.id == doc_id))
        is_locked = lock_result.scalar_one_or_none()

        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Документ заблокирован. Редактирование, назначение и снятие назначения невозможны."
            )

        # ✅ Делегируем обновление нижнему слою
        return await self._service.update(doc_id, request, user_id=user_id, **kwargs)

    async def delete(self, *args, **kwargs):
        return await self._service.delete(*args, **kwargs)

    async def get_logs(self, *args, **kwargs):
        return await self._service.get_logs(*args, **kwargs)

    async def assign_to_me(self, doc_id: int, user_id: int):
        """Назначить документ на текущего пользователя."""

        from app.reports.documents.schemas.document import DocumentUpdate
        return await self.update(doc_id, DocumentUpdate(assigned_to=user_id), user_id=user_id)

    async def assign_to_user(self, doc_id: int, assignee_id: int, current_user_id:int):

        """Назначить документ на указанного пользователя."""
        from app.reports.documents.schemas.document import DocumentUpdate
        return await self.update(doc_id, DocumentUpdate(assigned_to=assignee_id), user_id=current_user_id)

    async def unassign(self, doc_id: int):
        """Снять назначение с документа."""
        from app.reports.documents.schemas.document import DocumentUpdate
        return await self.update(doc_id, DocumentUpdate(assigned_to=None), user_id=None)


    # === Блокировка ===
    async def lock(self, doc_id: int, user_id: int):
        """Заблокировать документ."""
        from app.reports.documents.schemas.document import DocumentUpdate
        return await self._service.update(doc_id, DocumentUpdate(is_locked=True), user_id=user_id )

    async def unlock(self, doc_id: int, user_id: int):
        """Разблокировать документ."""
        from app.reports.documents.schemas.document import DocumentUpdate
        return await self._service.update(doc_id, DocumentUpdate(is_locked=False), user_id=user_id)

    # === Архив ===

    async def archive(self, doc_id: int, user_id: int):
        """Архивировать документ."""
        from app.reports.documents.schemas.document import DocumentUpdate
        result = await self._service.update(doc_id, DocumentUpdate(is_archived=True), user_id=user_id)

        chat_id = await self.get_chat_id(doc_id)
        if chat_id:
            from app.messages.public_services import PublicChatService
            chat_service = PublicChatService(self._service.db)
            await chat_service.archive(chat_id, user_id)
        return result
    
    async def unarchive(self, doc_id: int, user_id: int):
        """Разархивировать документ."""
        from app.reports.documents.schemas.document import DocumentUpdate
        result = await self._service.update(doc_id, DocumentUpdate(is_archived=False), user_id=user_id)

        chat_id = await self.get_chat_id(doc_id)
        if chat_id:
            from app.messages.public_services import PublicChatService
            chat_service = PublicChatService(self._service.db)
            await chat_service.unarchive(chat_id, user_id)
        return result

    # === Анонимизация ===
    async def anonymize(self, doc_id: int, user_id: int):
        """Анонимизировать документ."""
        return await self._service.anonymize(doc_id, user_id)

    # === Статус ===
    async def change_status(self, doc_id: int, status, user_id: int):
        """Изменить статус документа."""
        from app.reports.documents.schemas.document import DocumentUpdate
        return await self.update(doc_id, DocumentUpdate(status=status), user_id=user_id)

    # === Приоритет ===
    async def change_priority(self, doc_id: int, priority, user_id: int):
        """Изменить приоритет документа."""
        from app.reports.documents.schemas.document import DocumentUpdate
        return await self.update(doc_id, DocumentUpdate(priority=priority), user_id=user_id)

    # === Этап ===
    async def change_stage(self, doc_id: int, stage, user_id: int):
        """Изменить текущий этап документа."""
        from app.reports.documents.schemas.document import DocumentUpdate
        return await self.update(doc_id, DocumentUpdate(current_stage=stage), user_id=user_id)

    # === Язык ===
    async def change_language(self, doc_id: int, language, user_id: int):
        """Изменить язык документа."""
        from app.reports.documents.schemas.document import DocumentUpdate
        return await self.update(doc_id, DocumentUpdate(language=language), user_id=user_id)

    async def get_chat_id(self, doc_id: int) -> Optional[int]:
        """Получить ID чата, привязанного к документу."""
        from app.messages.models import Chat
        from sqlalchemy import select
        result = await self._service.db.execute(
            select(Chat.id).where(Chat.document_id == doc_id)
        )
        return result.scalar_one_or_none()

    async def get_attachments(self, doc_id: int):
        """Получить вложения документа (без удалённых)."""
        from app.reports.models import DocumentAttachment
        from sqlalchemy import select
        result = await self._service.db.execute(
            select(DocumentAttachment)
            .where(DocumentAttachment.document_id == doc_id, DocumentAttachment.is_deleted == False)
            .order_by(DocumentAttachment.uploaded_at.asc())
        )
        return result.scalars().all()

    async def add_attachment(self, doc_id: int, file_path: str, original_filename: str, file_type: str, uploaded_by: int):
        """Добавить вложение к документу."""
        from app.reports.models import DocumentAttachment
        attachment = DocumentAttachment(
            document_id=doc_id,
            file_path=file_path,
            original_filename=original_filename,
            file_type=file_type,
            uploaded_by=uploaded_by,
        )
        self._service.db.add(attachment)
        await self._service.db.commit()
        await self._service.db.refresh(attachment)
        return attachment

    async def delete_attachment(self, attachment_id: int, user_id: int) -> bool:
        """Мягкое удаление вложения документа (is_deleted = True)."""
        from app.reports.models import DocumentAttachment, DocumentLog
        from sqlalchemy import select
        result = await self._service.db.execute(
            select(DocumentAttachment).where(DocumentAttachment.id == attachment_id)
        )
        attachment = result.scalar_one_or_none()
        if not attachment or attachment.is_deleted:
            return False

        attachment.is_deleted = True
        await self._service.db.flush()

        log = DocumentLog(
            document_id=attachment.document_id,
            user_id=user_id,
            action="ATTACHMENT_DELETED",
            new_value=f"Attachment {attachment_id} soft deleted",
        )
        self._service.db.add(log)
        await self._service.db.commit()

        return True
