from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy import select, asc, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.reports.documents.document_service import DocumentService
from app.reports.documents.document_models import Document
from app.reports.documents.schemas.document import (
    DocumentFilter, 
    DocumentResponse, 
    DocumentListResponse,
    DocumentUpdate,
)
from app.reports.models import DocumentAttachment, DocumentLog
from app.messages.models import Chat
from app.messages.public_services import PublicChatService


class PublicDocumentService:
    """Публичный слой документов (facade + orchestration)."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._service = DocumentService(db)

    # ========================
    # Базовые методы (проксирование)
    # ========================

    async def create(self, request):
        track_id = getattr(request, "track_id", None)
        logger.debug("Creating document", track_id=track_id)
        result = await self._service.create(request)
        logger.info("Document created successfully", doc_id=result.id)
        return result

    async def get_by_id(self, doc_id: int):
        logger.debug("Fetching document by ID", doc_id=doc_id)
        return await self._service.get_by_id(doc_id)

    async def get_by_track_id(self, track_id: str):
        logger.debug("Fetching document by track_id", track_id=track_id)
        return await self._service.get_by_track_id(track_id)

    async def get_all(self):
        logger.debug("Fetching all documents")
        return await self._service.get_all()

    async def list_filtered(
        self,
        filters: DocumentFilter,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentListResponse:
        """
        Получение списка документов с фильтрацией, сортировкой и пагинацией.
        """
        logger.debug("Listing documents with filters", skip=skip, limit=limit)
        
        query = select(Document)
        count_query = select(func.count(Document.id))

        # === ФИЛЬТРАЦИЯ ===
        if filters.track_id:
            query = query.where(Document.track_id == filters.track_id)
            count_query = count_query.where(Document.track_id == filters.track_id)
        
        if filters.created_by is not None:
            query = query.where(Document.created_by == filters.created_by)
            count_query = count_query.where(Document.created_by == filters.created_by)
        
        if filters.assigned_to is not None:
            query = query.where(Document.assigned_to == filters.assigned_to)
            count_query = count_query.where(Document.assigned_to == filters.assigned_to)
        
        if filters.doc_type_id is not None:
            query = query.where(Document.doc_type_id == filters.doc_type_id)
            count_query = count_query.where(Document.doc_type_id == filters.doc_type_id)

        # Enum-поля: валидатор Pydantic уже привёл значения к Enum, берём .value напрямую
        if filters.status is not None:
            query = query.where(Document.status == filters.status.value)
            count_query = count_query.where(Document.status == filters.status.value)
        
        if filters.current_stage is not None:
            query = query.where(Document.current_stage == filters.current_stage.value)
            count_query = count_query.where(Document.current_stage == filters.current_stage.value)
        
        if filters.language is not None:
            query = query.where(Document.language == filters.language.value)
            count_query = count_query.where(Document.language == filters.language.value)
        
        if filters.priority is not None:
            query = query.where(Document.priority == filters.priority.value)
            count_query = count_query.where(Document.priority == filters.priority.value)

        # Boolean-поля
        if filters.is_locked is not None:
            query = query.where(Document.is_locked == filters.is_locked)
            count_query = count_query.where(Document.is_locked == filters.is_locked)
        
        if filters.is_archived is not None:
            query = query.where(Document.is_archived == filters.is_archived)
            count_query = count_query.where(Document.is_archived == filters.is_archived)
        
        if filters.is_anonymized is not None:
            query = query.where(Document.is_anonymized == filters.is_anonymized)
            count_query = count_query.where(Document.is_anonymized == filters.is_anonymized)

        # Диапазон дат
        if filters.created_from is not None:
            query = query.where(Document.created_at >= filters.created_from)
            count_query = count_query.where(Document.created_at >= filters.created_from)
        
        if filters.created_to is not None:
            query = query.where(Document.created_at <= filters.created_to)
            count_query = count_query.where(Document.created_at <= filters.created_to)

        # === СОРТИРОВКА ===
        sort_column = getattr(Document, filters.sort_by, Document.id)
        if filters.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # === ПАГИНАЦИЯ ===
        query = query.offset(skip).limit(limit)

        # === ВЫПОЛНЕНИЕ ЗАПРОСОВ ===
        result = await self.db.execute(query)
        documents = result.scalars().all()
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # === КОНВЕРТАЦИЯ В PYDANTIC ===
        response_items = [
            DocumentResponse.model_validate(doc, from_attributes=True) 
            for doc in documents
        ]

        logger.info("Document list retrieved", total=total, returned=len(response_items))
        return DocumentListResponse(documents=response_items, total=total)

    async def delete(self, doc_id: int, user_id: int):
        logger.info("Deleting document", doc_id=doc_id, user_id=user_id)
        return await self._service.delete(doc_id)

    async def get_logs(self, doc_id: int):
        logger.debug("Fetching document logs", doc_id=doc_id)
        return await self._service.get_logs(doc_id)

    # ========================
    # Внутренние утилиты
    # ========================

    async def _ensure_not_locked(self, doc_id: int):
        logger.debug("Checking document lock status", doc_id=doc_id)
        result = await self.db.execute(
            select(Document.is_locked).where(Document.id == doc_id)
        )
        is_locked = result.scalar_one_or_none()

        if is_locked:
            logger.warning("Attempt to modify locked document", doc_id=doc_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Документ заблокирован"
            )

    def _update_payload(self, **kwargs) -> DocumentUpdate:
        """Единая точка создания DTO"""
        return DocumentUpdate(**kwargs)

    # ========================
    # UPDATE (центральный метод)
    # ========================

    async def update(self, doc_id: int, request: DocumentUpdate, user_id: Optional[int] = None):
        logger.debug("Updating document", doc_id=doc_id, user_id=user_id)
        await self._ensure_not_locked(doc_id)
        result = await self._service.update(doc_id, request, user_id=user_id)
        logger.info("Document updated", doc_id=doc_id, fields=request.model_dump(exclude_unset=True))
        return result

    # ========================
    # Назначения
    # ========================

    async def assign_to_me(self, doc_id: int, user_id: int):
        logger.info("Assigning document to self", doc_id=doc_id, user_id=user_id)
        return await self.update(doc_id, self._update_payload(assigned_to=user_id), user_id)

    async def assign_to_user(self, doc_id: int, assignee_id: int, current_user_id: int):
        logger.info("Assigning document to user", doc_id=doc_id, assignee_id=assignee_id, assigned_by=current_user_id)
        return await self.update(doc_id, self._update_payload(assigned_to=assignee_id), current_user_id)

    async def unassign(self, doc_id: int, user_id: int):
        logger.info("Unassigning document", doc_id=doc_id, user_id=user_id)
        return await self.update(doc_id, self._update_payload(assigned_to=None), user_id)

    # ========================
    # Блокировка (обходит lock-check)
    # ========================

    async def lock(self, doc_id: int, user_id: int):
        logger.info("Locking document", doc_id=doc_id, user_id=user_id)
        return await self._service.lock(doc_id, user_id)
        # return await self._service.update(doc_id, self._update_payload(is_locked=True), user_id)


    async def unlock(self, doc_id: int, user_id: int):
        logger.info("Unlocking document", doc_id=doc_id, user_id=user_id)
        return await self._service.unlock(doc_id, user_id)
        return await self._service.update(doc_id, self._update_payload(is_locked=False), user_id)

    # ========================
    # Архив
    # ========================

    async def archive(self, doc_id: int, user_id: int):
        logger.info("Archiving document", doc_id=doc_id, user_id=user_id)
        result = await self._service.update(
            doc_id, self._update_payload(is_archived=True), user_id
        )
        await self._sync_chat_archive(doc_id, user_id, archived=True)
        return result

    async def unarchive(self, doc_id: int, user_id: int):
        logger.info("Unarchiving document", doc_id=doc_id, user_id=user_id)
        result = await self._service.update(
            doc_id, self._update_payload(is_archived=False), user_id
        )
        await self._sync_chat_archive(doc_id, user_id, archived=False)
        return result

    async def _sync_chat_archive(self, doc_id: int, user_id: int, archived: bool):
        logger.debug("Syncing chat archive status", doc_id=doc_id, archived=archived)
        chat_id = await self.get_chat_id(doc_id)
        if not chat_id:
            logger.debug("No chat found for document, skipping sync", doc_id=doc_id)
            return

        chat_service = PublicChatService(self.db)
        if archived:
            await chat_service.archive(chat_id, user_id)
            logger.debug("Chat archived", chat_id=chat_id)
        else:
            await chat_service.unarchive(chat_id, user_id)
            logger.debug("Chat unarchived", chat_id=chat_id)

    # ========================
    # Прочие изменения
    # ========================

    async def anonymize(self, doc_id: int, user_id: int):
        logger.info("Anonymizing document", doc_id=doc_id, user_id=user_id)
        return await self._service.anonymize(doc_id, user_id)

    async def change_status(self, doc_id: int, status, user_id: int):
        logger.info("Changing document status", doc_id=doc_id, new_status=status, user_id=user_id)
        return await self.update(doc_id, self._update_payload(status=status), user_id)

    async def change_priority(self, doc_id: int, priority, user_id: int):
        logger.info("Changing document priority", doc_id=doc_id, new_priority=priority, user_id=user_id)
        return await self.update(doc_id, self._update_payload(priority=priority), user_id)

    async def change_stage(self, doc_id: int, stage, user_id: int):
        logger.info("Changing document stage", doc_id=doc_id, new_stage=stage, user_id=user_id)
        return await self.update(doc_id, self._update_payload(current_stage=stage), user_id)

    async def change_language(self, doc_id: int, language, user_id: int):
        logger.info("Changing document language", doc_id=doc_id, new_language=language, user_id=user_id)
        return await self.update(doc_id, self._update_payload(language=language), user_id)

    async def change_type(self, doc_id: int, doc_type_id: int, user_id: int):
        logger.info("Changing document type", doc_id=doc_id, new_doc_type_id=doc_type_id, user_id=user_id)
        return await self.update(doc_id, self._update_payload(doc_type_id=doc_type_id), user_id)

    # ========================
    # Chat
    # ========================

    async def get_chat_id(self, doc_id: int) -> Optional[int]:
        logger.debug("Fetching chat ID for document", doc_id=doc_id)
        result = await self.db.execute(
            select(Chat.id).where(Chat.document_id == doc_id)
        )
        return result.scalar_one_or_none()

    # ========================
    # Attachments
    # ========================

    async def get_attachments(self, doc_id: int) -> List[DocumentAttachment]:
        logger.debug("Fetching document attachments", doc_id=doc_id)
        result = await self.db.execute(
            select(DocumentAttachment)
            .where(
                DocumentAttachment.document_id == doc_id,
                DocumentAttachment.is_deleted.is_(False)
            )
            .order_by(DocumentAttachment.uploaded_at.asc())
        )
        return result.scalars().all()

    async def add_attachment(
        self,
        doc_id: int,
        file_path: str,
        original_filename: str,
        file_type: str,
        uploaded_by: int
    ) -> DocumentAttachment:
        logger.info("Adding attachment", doc_id=doc_id, filename=original_filename, user_id=uploaded_by)

        attachment = DocumentAttachment(
            document_id=doc_id,
            file_path=file_path,
            original_filename=original_filename,
            file_type=file_type,
            uploaded_by=uploaded_by,
        )

        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)

        logger.info("Attachment added successfully", attachment_id=attachment.id)
        return attachment

    async def delete_attachment(self, attachment_id: int, user_id: int) -> bool:
        logger.info("Deleting attachment", attachment_id=attachment_id, user_id=user_id)
        
        result = await self.db.execute(
            select(DocumentAttachment).where(DocumentAttachment.id == attachment_id)
        )
        attachment = result.scalar_one_or_none()

        if not attachment or attachment.is_deleted:
            logger.warning("Attachment not found or already deleted", attachment_id=attachment_id)
            return False

        attachment.is_deleted = True
        await self.db.flush()

        log = DocumentLog(
            document_id=attachment.document_id,
            user_id=user_id,
            action="ATTACHMENT_DELETED",
            new_value=f"Attachment {attachment_id} soft deleted",
        )

        self.db.add(log)
        await self.db.commit()

        logger.info("Attachment deleted successfully", attachment_id=attachment_id)
        return True