from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from loguru import logger

from app.reports.correction.correction_models import Correction, CorrectionStatus
from app.reports.models import ProblemRegistration, Document, DocumentType
from app.reports.correction.correction_schemas import (
    CorrectionCreate,
    CorrectionUpdate,
    CorrectionResponse,
    CorrectionFilter,
)
from app.reports.documents.schemas.document import DocumentCreate, DocumentStage
from app.reports.documents.document_public_service import PublicDocumentService
from app.messages.models import Chat, Message, MessageAttachment
from app.auth.models import User


class CorrectionService:
    _SORT_COLUMNS = {
        "id": Correction.id,
        "title": Correction.title,
        "status": Correction.status,
        "planned_date": Correction.planned_date,
        "created_at": Correction.created_at,
        "updated_at": Correction.updated_at,
        "track_id": Document.track_id,
        "doc_status": Document.status,
        "doc_created_at": Document.created_at,
    }

    def __init__(self, db: AsyncSession, doc_service: PublicDocumentService):
        self.db = db
        self.doc_service = doc_service
        logger.debug("CorrectionService initialized")

    # ==========================================
    # 🆕 CREATE
    # ==========================================
    async def create(self, request: CorrectionCreate, created_by: int) -> CorrectionResponse:
        logger.info("Creating correction", created_by=created_by, title=request.title)
        
        # 1. Проверка заявки
        pr_exists = await self.db.execute(
            select(func.count()).select_from(Document).where(
                Document.id == request.target_document_id
            )
        )
        if pr_exists.scalar_one() == 0:
            logger.warning("target_document_id not found", pr_id=request.target_document_id)
            raise HTTPException(status_code=404, detail="target_document_id not found")
        logger.debug("target_document_id validated", pr_id=request.target_document_id)

        # 2. Тип документа
        doc_type_id = (await self.db.execute(
            select(DocumentType.id).where(DocumentType.code == "CorrectiveAction")
        )).scalar_one_or_none()
        if not doc_type_id:
            logger.error("DocumentType 'CorrectiveAction' not found in DB")
            raise HTTPException(status_code=500, detail="Missing document type configuration")
        logger.debug("DocumentType resolved", doc_type_id=doc_type_id)

        # 3. Создание документа
        doc_resp = await self.doc_service.create(DocumentCreate(
            created_by=created_by,
            status=request.doc_status,
            doc_type_id=doc_type_id,
            current_stage=DocumentStage.NEW,
            language=request.doc_language,
            priority=request.doc_priority,
            attachment_files=request.attachment_files,
        ))
        logger.debug("Underlying document created", doc_id=doc_resp.id, track_id=doc_resp.track_id)

        # 4. Создание коррекции
        correction = Correction(
            document_id=doc_resp.id,
            target_document_id=request.target_document_id,
            title=request.title,
            description=request.description,
            corrective_action=request.corrective_action,
            status=request.status.value if hasattr(request.status, "value") else request.status,
            planned_date=request.planned_date,
            completed_date=request.completed_date,
            created_by=created_by,
        )
        self.db.add(correction)
        await self.db.flush()
        logger.debug("Correction entity added to session", correction_id=correction.id)

        # 5. Чат + первое сообщение
        chat = Chat(name=f"Коррекция #{doc_resp.track_id} - {request.title}", document_id=doc_resp.id)
        creator_user = (await self.db.execute(select(User).where(User.id == created_by))).scalar_one_or_none()
        if creator_user:
            chat.participants = [creator_user]
        self.db.add(chat)
        await self.db.flush()
        logger.debug("Chat created for correction", chat_id=chat.id)

        if request.title or request.corrective_action:
            first_msg = Message(
                chat_id=chat.id,
                sender_id=created_by,
                content=(
                    f"<p><b>Тема:</b> {request.title}</p>"
                    f"<p><b>Описание:</b> {request.description or '—'}</p>"
                    f"<p><b>Действия:</b> {request.corrective_action}</p>"
                ),
            )
            self.db.add(first_msg)
            logger.debug("First message added to chat", message_id=first_msg.id)

            if request.attachment_files:
                await self.db.flush()
                for att in request.attachment_files:
                    self.db.add(MessageAttachment(
                        message_id=first_msg.id,
                        file_path=att.file_path,
                        original_filename=att.original_filename,
                        file_type=att.file_type or "application/octet-stream",
                    ))
                logger.debug("Attachments added to first message", count=len(request.attachment_files))

        await self.db.commit()
        logger.info("Correction created successfully", correction_id=correction.id, track_id=doc_resp.track_id)
        
        return await self._get_correction_row(Correction.id == correction.id)

    # ==========================================
    # 🔍 READ
    # ==========================================
    async def get_by_id(self, correction_id: int) -> Optional[CorrectionResponse]:
        logger.debug("Fetching correction by ID", correction_id=correction_id)
        result = await self._get_correction_row(Correction.id == correction_id)
        if not result:
            logger.debug("Correction not found by ID", correction_id=correction_id)
        return result

    async def get_by_document_id(self, doc_id: int) -> Optional[CorrectionResponse]:
        logger.debug("Fetching correction by document ID", doc_id=doc_id)
        result = await self._get_correction_row(Correction.document_id == doc_id)
        if not result:
            logger.debug("Correction not found by doc_id", doc_id=doc_id)
        return result

    async def get_by_track_id(self, track_id: str) -> Optional[CorrectionResponse]:
        logger.debug("Fetching correction by track_id", track_id=track_id)
        result = await self._get_correction_row(Document.track_id == track_id)
        if not result:
            logger.debug("Correction not found by track_id", track_id=track_id)
        return result

    async def get_by_target_document_id(self, pr_id: int) -> Optional[CorrectionResponse]:
        logger.debug("Fetching correction by target_document_id", pr_id=pr_id)
        result = await self._get_correction_row(Correction.target_document_id == pr_id)
        if not result:
            logger.debug("Correction not found by pr_id", pr_id=pr_id)
        return result

    async def _get_correction_row(self, where_clause) -> Optional[CorrectionResponse]:
        logger.debug("Executing correction query with JOIN")
        result = await self.db.execute(
            select(Correction, Document)
            .join(Document, Correction.document_id == Document.id)
            .where(where_clause)
            .options(
                selectinload(Correction.creator),
                selectinload(Correction.completer),
                selectinload(Correction.verifier),
            )
        )
        row = result.first()
        if row:
            logger.debug("Correction row fetched successfully", correction_id=row[0].id)
        return self._row_to_response(row) if row else None

    # ==========================================
    # 📝 UPDATE
    # ==========================================
    async def update(self, correction_id: int, request: CorrectionUpdate) -> Optional[CorrectionResponse]:
        logger.info("Updating correction", correction_id=correction_id)
        
        correction = (await self.db.execute(
            select(Correction).where(Correction.id == correction_id)
        )).scalar_one_or_none()
        
        if not correction:
            logger.warning("Correction not found for update", correction_id=correction_id)
            return None

        update_data = request.model_dump(exclude_unset=True)
        if not update_data:
            logger.debug("No fields to update, returning current state")
            return await self.get_by_id(correction_id)

        # Убираем защищённые поля
        for fk in ("document_id", "target_document_id"):
            update_data.pop(fk, None)

        logger.debug("Applying update fields", fields=list(update_data.keys()))
        
        for field, value in list(update_data.items()):
            # Нормализация статуса
            if field == "status":
                value = value.value if hasattr(value, "value") else value
                if not value:
                    value = CorrectionStatus.PLANNED.value
                logger.debug("Normalized status field", value=value)

            # Игнор пустых обязательных полей
            if field in ("title", "corrective_action") and not value:
                update_data.pop(field)
                logger.debug("Skipped empty required field", field=field)
                continue

            # Валидация пользователей
            if field in ("completed_by", "verified_by") and value is not None:
                user_exists = (await self.db.execute(
                    select(func.count()).select_from(User).where(User.id == value)
                )).scalar_one()
                if user_exists == 0:
                    update_data.pop(field)
                    logger.warning("Invalid user_id in update, ignoring", field=field, user_id=value)

        for field, value in update_data.items():
            setattr(correction, field, value)
            logger.debug(f"Set field {field} = {value!r}")

        await self.db.commit()
        await self.db.refresh(correction)
        logger.info("Correction updated successfully", correction_id=correction_id)
        return await self.get_by_id(correction_id)

    # ==========================================
    # 🗑 DELETE
    # ==========================================
    async def delete(self, correction_id: int) -> bool:
        logger.info("Deleting correction", correction_id=correction_id)
        
        correction = (await self.db.execute(
            select(Correction).where(Correction.id == correction_id)
        )).scalar_one_or_none()
        
        if not correction:
            logger.warning("Correction not found for deletion", correction_id=correction_id)
            return False
            
        logger.debug("Deleting associated document", doc_id=correction.document_id)
        await self.doc_service.delete(correction.document_id)
        
        await self.db.commit()
        logger.info("Correction deleted successfully", correction_id=correction_id)
        return True

    # ==========================================
    # 📊 LIST + FILTER
    # ==========================================
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[CorrectionFilter] = None,
    ) -> dict:
        logger.debug("Listing corrections", skip=skip, limit=limit, filters=filters.model_dump() if filters else None)
        
        conditions = []
        if filters:
            # Коррекция
            if filters.title: 
                conditions.append(Correction.title.ilike(f"%{filters.title}%"))
                logger.debug("Filter applied: title LIKE", pattern=f"%{filters.title}%")
            if filters.description: 
                conditions.append(Correction.description.ilike(f"%{filters.description}%"))
                logger.debug("Filter applied: description LIKE", pattern=f"%{filters.description}%")
            if filters.status is not None: 
                conditions.append(Correction.status == (filters.status.value if hasattr(filters.status, "value") else filters.status))
                logger.debug("Filter applied: status", value=filters.status)
            if filters.planned_date_from: 
                conditions.append(Correction.planned_date >= filters.planned_date_from)
                logger.debug("Filter applied: planned_date_from", value=filters.planned_date_from)
            if filters.planned_date_to: 
                conditions.append(Correction.planned_date <= filters.planned_date_to)
                logger.debug("Filter applied: planned_date_to", value=filters.planned_date_to)

            # Документ
            if filters.track_id: 
                conditions.append(Document.track_id.ilike(f"%{filters.track_id}%"))
                logger.debug("Filter applied: track_id LIKE", pattern=f"%{filters.track_id}%")
            if filters.doc_created_from: 
                conditions.append(Document.created_at >= filters.doc_created_from)
                logger.debug("Filter applied: doc_created_from", value=filters.doc_created_from)
            if filters.doc_created_to: 
                conditions.append(Document.created_at <= filters.doc_created_to)
                logger.debug("Filter applied: doc_created_to", value=filters.doc_created_to)
            if filters.doc_status is not None: 
                conditions.append(Document.status == (filters.doc_status.value if hasattr(filters.doc_status, "value") else filters.doc_status))
                logger.debug("Filter applied: doc_status", value=filters.doc_status)
            if filters.doc_type_id is not None: 
                conditions.append(Document.doc_type_id == filters.doc_type_id)
                logger.debug("Filter applied: doc_type_id", value=filters.doc_type_id)
            if filters.doc_current_stage is not None: 
                conditions.append(Document.current_stage == (filters.doc_current_stage.value if hasattr(filters.doc_current_stage, "value") else filters.doc_current_stage))
                logger.debug("Filter applied: doc_current_stage", value=filters.doc_current_stage)
            if filters.created_by is not None: 
                conditions.append(Document.created_by == filters.created_by)
                logger.debug("Filter applied: created_by", value=filters.created_by)
            if filters.assigned_to is not None: 
                conditions.append(Document.assigned_to == filters.assigned_to)
                logger.debug("Filter applied: assigned_to", value=filters.assigned_to)
            if filters.is_locked is not None: 
                conditions.append(Document.is_locked == filters.is_locked)
                logger.debug("Filter applied: is_locked", value=filters.is_locked)

        base_query = select(Correction, Document).join(Document, Correction.document_id == Document.id)
        if conditions:
            base_query = base_query.where(and_(*conditions))
            logger.debug("Query built with conditions", count=len(conditions))

        # Count
        count_stmt = select(func.count(Correction.id)).join(Document, Correction.document_id == Document.id)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar_one()
        logger.debug("Total count calculated", total=total)

        # Sort & Pagination
        sort_by = (filters.sort_by or "id") if filters else "id"
        sort_order = ((filters.sort_order or "desc").lower()) if filters else "desc"
        sort_col = self._SORT_COLUMNS.get(sort_by, Correction.id)
        order_fn = sort_col.asc if sort_order == "asc" else sort_col.desc
        logger.debug("Sorting applied", by=sort_by, order=sort_order)

        result = await self.db.execute(
            base_query
            .options(
                selectinload(Correction.creator),
                selectinload(Correction.completer),
                selectinload(Correction.verifier),
            )
            .order_by(order_fn())
            .offset(skip)
            .limit(limit)
        )

        items = [self._row_to_response(row) for row in result.all()]
        logger.info("Corrections retrieved", total=total, returned=len(items), skip=skip, limit=limit)
        
        return {
            "items": items,
            "total": total
        }

    # ==========================================
    # 🔄 HELPER: Row → Response
    # ==========================================
    def _row_to_response(self, row) -> CorrectionResponse:
        """Конвертация JOIN-строки в Pydantic-модель."""
        corr, doc = row
        logger.debug("Converting row to CorrectionResponse", correction_id=corr.id)
        return CorrectionResponse(
            id=corr.id,
            document_id=corr.document_id,
            target_document_id=corr.target_document_id,
            title=corr.title,
            description=corr.description,
            corrective_action=corr.corrective_action,
            status=corr.status,
            planned_date=corr.planned_date,
            completed_date=corr.completed_date,
            created_at=corr.created_at,
            updated_at=corr.updated_at,
            track_id=doc.track_id,
            doc_created_at=doc.created_at,
            doc_current_stage=doc.current_stage,
            doc_status=doc.status,
            doc_language=doc.language,
            doc_priority=doc.priority,
            assigned_to=doc.assigned_to,
            is_locked=doc.is_locked,
            is_archived=doc.is_archived,
            created_by=corr.created_by,
        )

    # ==========================================
    # 📦 DOCUMENT DELEGATION
    # ==========================================
    async def archive_document(self, doc_id: int, user_id: int) -> CorrectionResponse:
        logger.info("Archiving correction document", doc_id=doc_id, user_id=user_id)
        result = await self.doc_service.archive(doc_id, user_id)
        logger.info("Correction document archived", doc_id=doc_id)
        return result

    async def unarchive_document(self, doc_id: int, user_id: int) -> CorrectionResponse:
        logger.info("Unarchiving correction document", doc_id=doc_id, user_id=user_id)
        result = await self.doc_service.unarchive(doc_id, user_id)
        logger.info("Correction document unarchived", doc_id=doc_id)
        return result

    async def assign_user_to_document(self, doc_id: int, user_id: int, current_user_id: int) -> CorrectionResponse:
        logger.info("Assigning user to correction document", doc_id=doc_id, assignee_id=user_id, assigned_by=current_user_id)
        result = await self.doc_service.assign_to_user(doc_id, user_id, current_user_id)
        logger.info("User assigned to correction document", doc_id=doc_id, assignee_id=user_id)
        return result

    # ==========================================
    # 🔒 DOCUMENT LOCK/UNLOCK
    # ==========================================
    async def lock(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Блокировка документа коррекции для редактирования."""
        logger.info("Locking correction", correction_id=correction_id, user_id=user_id)
        
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Cannot lock: correction not found", correction_id=correction_id)
            return None

        if item.is_locked:
            logger.debug("Correction already locked", correction_id=correction_id)
            return item

        try:
            await self.doc_service.lock(item.document_id, user_id=user_id)
            logger.info("Correction locked", correction_id=correction_id)
            return await self.get_by_id(correction_id)
        except Exception as e:
            logger.warning("Lock failed for correction", correction_id=correction_id, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )

    async def unlock(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Разблокировка документа коррекции."""
        logger.info("Unlocking correction", correction_id=correction_id, user_id=user_id)
        
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Cannot unlock: correction not found", correction_id=correction_id)
            return None
            
        if not item.is_locked:
            logger.debug("Correction already unlocked", correction_id=correction_id)
            return item

        try:
            await self.doc_service.unlock(item.document_id, user_id=user_id)
            logger.info("Correction unlocked", correction_id=correction_id)
            return await self.get_by_id(correction_id)
        except Exception as e:
            logger.warning("Unlock failed for correction", correction_id=correction_id, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )