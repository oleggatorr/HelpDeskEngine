from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.orm import selectinload

from app.reports.models import ProblemRegistration, Document, DocumentType
from app.reports.problem_registrations.pr_schemas import (
    ProblemRegistrationCreate,
    ProblemRegistrationUpdate,
    ProblemRegistrationResponse,
    ProblemRegistration_DetaleUpdate,
    ProblemRegistrationFilter,
)
from app.reports.documents.schemas.document import DocumentCreate, DocumentStage
from app.reports.documents.document_public_service import PublicDocumentService
from app.messages.models import Chat, Message, MessageAttachment
from app.auth.models import User


class ProblemRegistrationService:
    """
    Сервис регистраций проблем.
    Использует PublicDocumentService для работы с документами.
    """

    def __init__(self, db: AsyncSession, doc_service: PublicDocumentService):
        self.db = db
        self.doc_service = doc_service

    async def create(self, request: ProblemRegistrationCreate, created_by: int) -> ProblemRegistrationResponse:
        logger.info("Creating problem registration", created_by=created_by, subject=request.subject)
        
        # Нормализуем FK-поля: 0 → None
        location_id = request.location_id or None

        # Получаем doc_type_id из справочника по коду "ProblemRegistration"
        doc_type_result = await self.db.execute(
            select(DocumentType.id).where(DocumentType.code == "ProblemRegistration")
        )
        doc_type_id = doc_type_result.scalar_one_or_none()
        if not doc_type_id:
            logger.error("DocumentType 'ProblemRegistration' not found in DB")
            raise HTTPException(status_code=500, detail="Missing document type configuration")

        # Проверяем существование FK
        if location_id:
            from app.knowledge_base.models import Location
            result = await self.db.execute(
                select(func.count()).select_from(Location).where(Location.id == location_id)
            )
            if result.scalar_one() == 0:
                logger.warning("Location ID not found, setting to None", location_id=location_id)
                location_id = None
                
        # 1. Создаём документ автоматически
        doc = await self.doc_service.create(DocumentCreate(
            created_by=created_by,
            status=request.doc_status,
            doc_type_id=doc_type_id,
            current_stage=DocumentStage.NEW,
            language=request.doc_language,
            priority=request.doc_priority,
            assigned_to=request.doc_assigned_to,
            attachment_files=request.attachment_files,
        ))
        logger.debug("Underlying document created", doc_id=doc.id, track_id=doc.track_id)

        # 2. Создаём регистрацию проблемы, привязанную к документу
        registration = ProblemRegistration(
            document_id=doc.id,
            subject=request.subject,
            detected_at=request.detected_at,
            location_id=location_id,
            description=request.description,
            nomenclature=request.nomenclature,
        )
        self.db.add(registration)

        # 3. Создаём чат, привязанный к документу
        chat = Chat(
            name=f"Обращение #{doc.track_id} - {request.subject}",
            document_id=doc.id,
        )
        creator = await self.db.execute(select(User).where(User.id == created_by))
        creator_user = creator.scalar_one_or_none()
        if creator_user:
            chat.participants = [creator_user]
        self.db.add(chat)

        # 4. Отправляем первое сообщение с темой и описанием проблемы
        if request.subject or request.description:
            await self.db.flush()
            first_message = Message(
                chat_id=chat.id,
                sender_id=created_by,
                content=f"<p>{request.subject or '—'}</p>{request.description or '—'}",
            )
            self.db.add(first_message)

            # 5. Копируем вложения документа в сообщение чата
            if getattr(request, 'attachment_files', None):
                await self.db.flush()
                for att_data in request.attachment_files:
                    message_attachment = MessageAttachment(
                        message_id=first_message.id,
                        file_path=att_data["file_path"],
                        original_filename=att_data.get("original_filename"),
                        file_type=att_data.get("file_type", "application/octet-stream"),
                    )
                    self.db.add(message_attachment)
                logger.debug("Added attachments to first message", count=len(request.attachment_files))

        await self.db.commit()
        await self.db.refresh(registration)

        logger.info("Problem registration created successfully", registration_id=registration.id, doc_track_id=doc.track_id)
        return await self.get_by_id(registration.id)

    async def get_by_id(self, registration_id: int) -> Optional[ProblemRegistrationResponse]:
        logger.debug("Fetching problem registration by ID", registration_id=registration_id)
        result = await self.db.execute(
            select(ProblemRegistration, Document)
            .join(Document, ProblemRegistration.document_id == Document.id)
            .where(ProblemRegistration.id == registration_id)
            .options(
                selectinload(ProblemRegistration.location),
                selectinload(ProblemRegistration.responsible_department),
            )
        )
        row = result.first()
        if not row:
            logger.debug("Problem registration not found", registration_id=registration_id)
            return None
        return self._row_to_response(row)

    async def get_by_document_id(self, doc_id: int) -> Optional[ProblemRegistrationResponse]:
        logger.debug("Fetching problem registration by document ID", doc_id=doc_id)
        result = await self.db.execute(
            select(ProblemRegistration, Document)
            .join(Document, ProblemRegistration.document_id == Document.id)
            .where(ProblemRegistration.document_id == doc_id)
            .options(
                selectinload(ProblemRegistration.location),
                selectinload(ProblemRegistration.responsible_department),
            )
        )
        row = result.first()
        if not row:
            logger.debug("Problem registration not found by doc_id", doc_id=doc_id)
            return None
        return self._row_to_response(row)

    async def get_by_track_id(self, track_id: str) -> Optional[ProblemRegistrationResponse]:
        logger.debug("Fetching problem registration by track_id", track_id=track_id)
        result = await self.db.execute(
            select(ProblemRegistration, Document)
            .join(Document, ProblemRegistration.document_id == Document.id)
            .where(Document.track_id == track_id)
            .options(
                selectinload(ProblemRegistration.location),
                selectinload(ProblemRegistration.responsible_department),
            )
        )
        row = result.first()
        if not row:
            logger.debug("Problem registration not found by track_id", track_id=track_id)
            return None
        return self._row_to_response(row)

    async def update(self, registration_id: int, request: ProblemRegistrationUpdate) -> Optional[ProblemRegistrationResponse]:
        logger.info("Updating problem registration", registration_id=registration_id)
        from app.reports.models import ProblemAction

        result = await self.db.execute(
            select(ProblemRegistration).where(ProblemRegistration.id == registration_id)
        )
        registration = result.scalar_one_or_none()
        if not registration:
            logger.warning("Registration not found for update", registration_id=registration_id)
            return None

        update_data = request.model_dump(exclude_unset=True)
        
        if update_data:
            logger.debug("Applying update fields", fields=list(update_data.keys()))
            
            if "location_id" in update_data and not update_data["location_id"]:
                update_data["location_id"] = None

            if update_data.get("location_id"):
                from app.knowledge_base.models import Location
                loc_result = await self.db.execute(
                    select(func.count()).select_from(Location).where(Location.id == update_data["location_id"])
                )
                if loc_result.scalar_one() == 0:
                    logger.warning("Invalid location_id in update, ignoring", location_id=update_data["location_id"])
                    update_data["location_id"] = None

            for field, value in update_data.items():
                if field == "action" and (value is None or value == ""):
                    value = ProblemAction.UNDEFINED.value
                
                if value is not None:
                    setattr(registration, field, value)
                    
            await self.db.commit()
            await self.db.refresh(registration)
            logger.info("Problem registration updated", registration_id=registration_id)

        return await self.get_by_id(registration_id)

    async def delete(self, registration_id: int) -> bool:
        logger.info("Deleting problem registration", registration_id=registration_id)
        result = await self.db.execute(
            select(ProblemRegistration).where(ProblemRegistration.id == registration_id)
        )
        registration = result.scalar_one_or_none()
        if not registration:
            logger.warning("Registration not found for deletion", registration_id=registration_id)
            return False

        await self.db.delete(registration)
        await self.db.commit()
        logger.info("Problem registration deleted", registration_id=registration_id)
        return True

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[ProblemRegistrationFilter] = None,
    ) -> dict:
        logger.debug("Listing problem registrations", skip=skip, limit=limit)
        conditions = []

        if filters:
            if filters.subject:
                conditions.append(ProblemRegistration.subject.ilike(f"%{filters.subject}%"))
            if filters.detected_from:
                conditions.append(ProblemRegistration.detected_at >= filters.detected_from)
            if filters.detected_to:
                conditions.append(ProblemRegistration.detected_at <= filters.detected_to)
            if filters.location_id is not None:
                conditions.append(ProblemRegistration.location_id == filters.location_id)
            if filters.description:
                conditions.append(ProblemRegistration.description.ilike(f"%{filters.description}%"))
            if filters.nomenclature:
                conditions.append(ProblemRegistration.nomenclature.ilike(f"%{filters.nomenclature}%"))
            if filters.approved_from:
                conditions.append(ProblemRegistration.approved_at >= filters.approved_from)
            if filters.approved_to:
                conditions.append(ProblemRegistration.approved_at <= filters.approved_to)
            if filters.action is not None:
                act_val = getattr(filters.action, 'value', filters.action)
                conditions.append(ProblemRegistration.action == act_val)
            if filters.responsible_department_id is not None:
                conditions.append(ProblemRegistration.responsible_department_id == filters.responsible_department_id)
            if filters.comment:
                conditions.append(ProblemRegistration.comment.ilike(f"%{filters.comment}%"))

            if filters.track_id:
                conditions.append(Document.track_id.ilike(f"%{filters.track_id}%"))
            if filters.doc_created_from:
                conditions.append(Document.created_at >= filters.doc_created_from)
            if filters.doc_created_to:
                conditions.append(Document.created_at <= filters.doc_created_to)
            if filters.doc_status is not None:
                status_val = getattr(filters.doc_status, 'value', filters.doc_status)
                conditions.append(Document.status == status_val)
            if filters.doc_type_id is not None:
                conditions.append(Document.doc_type_id == filters.doc_type_id)
            if filters.doc_current_stage:
                try:
                    stage_val = DocumentStage[filters.doc_current_stage]
                    conditions.append(Document.current_stage == stage_val)
                except KeyError:
                    pass
            if filters.created_by is not None:
                conditions.append(Document.created_by == filters.created_by)
            if filters.assigned_to is not None:
                if filters.assigned_to == -1:
                    conditions.append(Document.assigned_to.is_(None))
                elif filters.assigned_to > 0:
                    conditions.append(Document.assigned_to == filters.assigned_to)
            if filters.is_locked is not None:
                conditions.append(Document.is_locked == filters.is_locked)

        base_query = select(ProblemRegistration, Document).join(
            Document, ProblemRegistration.document_id == Document.id
        ).options(
            selectinload(ProblemRegistration.location),
            selectinload(ProblemRegistration.responsible_department)
        )

        if conditions:
            base_query = base_query.where(and_(*conditions))

        count_subq = base_query.subquery()
        count_query = select(func.count()).select_from(count_subq)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        sort_by = filters.sort_by if filters and filters.sort_by else "id"
        sort_order = (filters.sort_order if filters and filters.sort_order else "desc").lower()

        sort_col = getattr(ProblemRegistration, sort_by, None) or getattr(Document, sort_by, ProblemRegistration.id)
        order_fn = sort_col.asc if sort_order == "asc" else sort_col.desc

        final_query = base_query.order_by(order_fn()).offset(skip).limit(limit)

        result = await self.db.execute(final_query)
        rows = result.all()
        items = [self._row_to_response(row) for row in rows]

        logger.info("Problem registrations retrieved", total=total, returned=len(items))
        return {"items": items, "total": total}

    def _row_to_response(self, row) -> ProblemRegistrationResponse:
        """Конвертация строки (registration, document) в Response."""
        from app.reports.models import DocumentStage as DocumentStageEnum

        reg, doc = row
        stage = doc.current_stage

        if stage is None:
            stage_str = None
        elif hasattr(stage, 'name'):
            stage_str = stage.name
        elif hasattr(stage, 'value'):
            stage_str = stage.value if isinstance(stage.value, str) else DocumentStageEnum(stage.value).name
        elif isinstance(stage, int):
            try:
                stage_str = DocumentStageEnum(stage).name
            except ValueError:
                stage_str = str(stage)
        else:
            stage_str = str(stage)

        return ProblemRegistrationResponse(
            id=reg.id,
            document_id=reg.document_id,
            track_id=doc.track_id,
            doc_created_at=doc.created_at,
            doc_current_stage=stage_str,
            doc_status=doc.status.value if hasattr(doc.status, 'value') else doc.status,
            is_locked=doc.is_locked,
            is_archived=doc.is_archived,
            assigned_to=doc.assigned_to,
            subject=reg.subject,
            detected_at=reg.detected_at,
            location_id=reg.location_id,
            description=reg.description,
            nomenclature=reg.nomenclature,
            approved_at=reg.approved_at,
            action=reg.action.value if hasattr(reg.action, 'value') else reg.action,
            responsible_department_id=reg.responsible_department_id,
            comment=reg.comment,
            location_name=reg.location.name if reg.location else None,
            department_name=reg.responsible_department.name if reg.responsible_department else None,
            created_by=doc.created_by,
        )

    async def update_response_details(
        self, 
        registration_id: int, 
        request: ProblemRegistration_DetaleUpdate
    ) -> Optional[ProblemRegistrationResponse]:
        logger.info("Updating registration response details", registration_id=registration_id)
        result = await self.db.execute(
            select(ProblemRegistration).where(ProblemRegistration.id == registration_id)
        )
        registration = result.scalar_one_or_none()
        if not registration:
            logger.warning("Registration not found for details update", registration_id=registration_id)
            return None

        update_data = request.model_dump(exclude_unset=True)
        if update_data:
            if "responsible_department_id" in update_data and not update_data["responsible_department_id"]:
                update_data["responsible_department_id"] = None

            if update_data.get("responsible_department_id"):
                from app.knowledge_base.models import Department
                dept_exists = await self.db.execute(
                    select(func.count()).select_from(Department).where(
                        Department.id == update_data["responsible_department_id"]
                    )
                )
                if dept_exists.scalar_one() == 0:
                    logger.warning("Invalid department_id in details update, ignoring", dept_id=update_data["responsible_department_id"])
                    update_data["responsible_department_id"] = None

            for field, value in update_data.items():
                if field == "action" and hasattr(value, "value"):
                    value = value.value
                setattr(registration, field, value)

            await self.db.commit()
            await self.db.refresh(registration)
            logger.info("Registration details updated", registration_id=registration_id)

        return await self.get_by_id(registration_id)

    async def archive_document(self, doc_id: int, user_id: int) -> ProblemRegistrationResponse:
        logger.info("Archiving problem registration document", doc_id=doc_id, user_id=user_id)
        return await self.doc_service.archive(doc_id, user_id)

    async def unarchive_document(self, doc_id: int, user_id: int) -> ProblemRegistrationResponse:
        logger.info("Unarchiving problem registration document", doc_id=doc_id, user_id=user_id)
        return await self.doc_service.unarchive(doc_id, user_id)

    async def assign_user_to_document(self, doc_id: int, user_id: int, current_user_id: int) -> ProblemRegistrationResponse:
        logger.info("Assigning user to document", doc_id=doc_id, assignee_id=user_id, assigned_by=current_user_id)
        return await self.doc_service.assign_to_user(doc_id, user_id, current_user_id)

    async def lock(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        logger.info("Locking problem registration", registration_id=registration_id, user_id=user_id)
        item = await self.get_by_id(registration_id)
        if not item:
            logger.warning("Cannot lock: registration not found", registration_id=registration_id)
            return None

        if item.is_locked:
            logger.debug("Registration already locked", registration_id=registration_id)
            return item

        try:
            await self.doc_service.lock(item.document_id, user_id=user_id)
            logger.info("Problem registration locked", registration_id=registration_id)
            return await self.get_by_id(registration_id)
        except Exception as e:
            logger.warning("Lock failed for registration", registration_id=registration_id, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )

    async def unlock(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        logger.info("Unlocking problem registration", registration_id=registration_id, user_id=user_id)
        item = await self.get_by_id(registration_id)
        if not item:
            logger.warning("Cannot unlock: registration not found", registration_id=registration_id)
            return None
            
        if not item.is_locked:
            logger.debug("Registration already unlocked", registration_id=registration_id)
            return item

        try:
            await self.doc_service.unlock(item.document_id, user_id=user_id)
            logger.info("Problem registration unlocked", registration_id=registration_id)
            return await self.get_by_id(registration_id)
        except Exception as e:
            logger.warning("Unlock failed for registration", registration_id=registration_id, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )