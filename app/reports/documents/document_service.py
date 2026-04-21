from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.reports.models import Document, DocumentLog, DocumentType, DocumentAttachment
from app.reports.documents.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
    DocumentStage,
    generate_track_id,
)


class DocumentService:
    """
    Сервис документов.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request: DocumentCreate) -> DocumentResponse:
        track_id = request.track_id or generate_track_id()

        # Если doc_type_id не указан — берём из справочника по коду "Empty"
        if not request.doc_type_id:
            doc_type_result = await self.db.execute(
                select(DocumentType.id).where(DocumentType.code == "Empty")
            )
            request.doc_type_id = doc_type_result.scalar_one_or_none()
        else:
            # Проверяем существование FK
            result = await self.db.execute(
                select(func.count()).select_from(DocumentType).where(DocumentType.id == request.doc_type_id)
            )
            if result.scalar_one() == 0:
                request.doc_type_id = None

        if request.created_by:
            from app.auth.models import User
            result = await self.db.execute(
                select(func.count()).select_from(User).where(User.id == request.created_by)
            )
            if result.scalar_one() == 0:
                request.created_by = None
        else:
            request.created_by = None

        doc = Document(
            track_id=track_id,
            created_by=request.created_by,
            status=request.status.value if hasattr(request.status, 'value') else request.status,
            doc_type_id=request.doc_type_id,
            current_stage=request.current_stage,
            is_locked=request.is_locked,
            is_archived=request.is_archived,
            is_anonymized=request.is_anonymized,
            language=request.language.value if hasattr(request.language, 'value') else request.language,
            priority=request.priority.value if hasattr(request.priority, 'value') else request.priority,
            assigned_to=request.assigned_to or None,
        )
        self.db.add(doc)
        await self.db.flush()

        # Вложения — сохраняем после flush (есть doc.id)
        if getattr(request, 'attachment_files', None):
            for att_data in request.attachment_files:
                attachment = DocumentAttachment(
                    document_id=doc.id,
                    file_path=att_data["file_path"],
                    original_filename=att_data.get("original_filename"),
                    file_type=att_data.get("file_type", "application/octet-stream"),
                    uploaded_by=request.created_by or None,
                )
                self.db.add(attachment)
        await self.db.flush()
        await self.db.refresh(doc)

        # Логирование создания
        log = DocumentLog(
            document_id=doc.id,
            user_id=request.created_by,
            action="CREATED",
            new_value=f"Document {doc.track_id} created",
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(doc)

        return DocumentResponse.model_validate(doc)

    async def get_by_id(self, doc_id: int) -> Optional[DocumentResponse]:
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        return DocumentResponse.model_validate(doc) if doc else None

    async def get_by_track_id(self, track_id: str) -> Optional[DocumentResponse]:
        result = await self.db.execute(
            select(Document).where(Document.track_id == track_id)
        )
        doc = result.scalar_one_or_none()
        return DocumentResponse.model_validate(doc) if doc else None

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        doc_type_id: Optional[int] = None,
        status=None,
        current_stage: Optional[DocumentStage] = None,
        created_by: Optional[int] = None,
    ) -> DocumentListResponse:
        return await self.list_filtered(
            skip=skip, limit=limit,
            doc_type_id=doc_type_id, status=status,
            current_stage=current_stage, created_by=created_by,
        )

    async def list_filtered(
        self,
        skip: int = 0,
        limit: int = 100,
        doc_type_id: Optional[int] = None,
        status=None,
        current_stage: Optional[DocumentStage] = None,
        created_by: Optional[int] = None,
        assigned_to: Optional[int] = None,
        track_id: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        is_locked: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        is_anonymized: Optional[bool] = None,
        language=None,
        priority=None,
        sort_by: str = "id",
        sort_order: str = "desc",
    ) -> DocumentListResponse:
        conditions = []

        if track_id is not None:
            conditions.append(Document.track_id.ilike(f"%{track_id}%"))
        if status is not None:
            status_value = status.value if hasattr(status, 'value') else status
            conditions.append(Document.status == status_value)
        if doc_type_id is not None:
            conditions.append(Document.doc_type_id == doc_type_id)
        if current_stage is not None:
            conditions.append(Document.current_stage == current_stage)
        if is_locked is not None:
            conditions.append(Document.is_locked == is_locked)
        if is_archived is not None:
            conditions.append(Document.is_archived == is_archived)
        if is_anonymized is not None:
            conditions.append(Document.is_anonymized == is_anonymized)
        if language is not None:
            lang_value = language.value if hasattr(language, 'value') else language
            conditions.append(Document.language == lang_value)
        if priority is not None:
            priority_value = priority.value if hasattr(priority, 'value') else priority
            conditions.append(Document.priority == priority_value)
        if created_by is not None:
            conditions.append(Document.created_by == created_by)
        if assigned_to is not None:
            conditions.append(Document.assigned_to == assigned_to)
        if created_from is not None:
            conditions.append(Document.created_at >= created_from)
        if created_to is not None:
            conditions.append(Document.created_at <= created_to)

        query = select(Document)
        if conditions:
            from sqlalchemy import and_
            query = query.where(and_(*conditions))

        # Счётчик
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Сортировка
        sort_col = getattr(Document, sort_by, Document.id)
        order_fn = sort_col.asc if sort_order == "asc" else sort_col.desc
        query = query.order_by(order_fn()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        docs = result.scalars().all()

        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(d) for d in docs],
            total=total,
        )

    async def update(self, doc_id: int, request, user_id: int) -> DocumentResponse:
        """Обновление полей документа."""
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        update_data = request.model_dump(exclude_unset=True)
        if update_data:
            # Нормализуем FK-поля: 0 → None
            if "doc_type_id" in update_data and not update_data["doc_type_id"]:
                update_data["doc_type_id"] = None
            if "assigned_to" in update_data and not update_data["assigned_to"]:
                update_data["assigned_to"] = None

            # Проверяем существование пользователя при назначении
            if update_data.get("assigned_to"):
                from app.auth.models import User
                user_result = await self.db.execute(
                    select(func.count()).select_from(User).where(User.id == update_data["assigned_to"])
                )
                if user_result.scalar_one() == 0:
                    raise ValueError(f"User {update_data['assigned_to']} not found")

            for field, value in update_data.items():
                # Конвертируем enum-значения
                if field == "status" and value is not None:
                    from app.reports.enums import DocumentStatus
                    value = DocumentStatus(value) if isinstance(value, str) else value
                elif field == "language" and value is not None:
                    from app.reports.enums import DocumentLanguage
                    value = DocumentLanguage(value) if isinstance(value, str) else value
                elif field == "priority" and value is not None:
                    from app.reports.enums import DocumentPriority
                    value = DocumentPriority(value) if isinstance(value, str) else value
                elif field == "current_stage" and value is not None:
                    from app.reports.enums import DocumentStage
                    value = DocumentStage(value) if isinstance(value, str) else value
                setattr(doc, field, value)
            await self.db.flush()

            # Логирование
            action = "UPDATED"
            if "assigned_to" in update_data:
                action = "ASSIGNMENT_CHANGED"

            log = DocumentLog(
                document_id=doc_id,
                user_id=user_id,
                action=action,
                new_value=f"Fields updated: {', '.join(update_data.keys())}",
            )
            self.db.add(log)
            await self.db.commit()
            await self.db.refresh(doc)

        return DocumentResponse.model_validate(doc)

    async def update_stage(self, doc_id: int, stage: DocumentStage, user_id: int) -> DocumentResponse:
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        old_stage = doc.current_stage.value if isinstance(doc.current_stage, DocumentStage) else str(doc.current_stage)

        doc.current_stage = stage
        await self.db.flush()

        # Логирование
        log = DocumentLog(
            document_id=doc_id,
            user_id=user_id,
            action="STAGE_CHANGED",
            field_name="current_stage",
            old_value=old_stage,
            new_value=stage.value,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(doc)

        return DocumentResponse.model_validate(doc)

    async def delete(self, doc_id: int) -> bool:
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return False

        await self.db.delete(doc)
        await self.db.commit()
        return True

    async def anonymize(self, doc_id: int, user_id: int) -> DocumentResponse:
        """Анонимизировать документ (скрыть персональные данные)."""
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        doc.is_anonymized = True
        await self.db.flush()

        # Анонимизируем все чаты, связанные с документом
        from app.messages.models import Chat
        chats_result = await self.db.execute(
            select(Chat).where(Chat.document_id == doc_id)
        )
        chats = chats_result.scalars().all()
        for chat in chats:
            chat.is_anonymized = True

        log = DocumentLog(
            document_id=doc_id,
            user_id=user_id,
            action="ANONYMIZED",
            new_value="Document anonymized (chats anonymized too)",
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(doc)

        return DocumentResponse.model_validate(doc)

    async def get_logs(self, doc_id: int, skip: int = 0, limit: int = 100) -> List[dict]:
        result = await self.db.execute(
            select(DocumentLog)
            .where(DocumentLog.document_id == doc_id)
            .order_by(DocumentLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        logs = result.scalars().all()
        return [
            {
                "id": log.id,
                "document_id": log.document_id,
                "user_id": log.user_id,
                "action": log.action,
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "created_at": log.created_at,
            }
            for log in logs
        ]

    async def archive(self, doc_id: int, user_id: int) -> DocumentResponse:
        """Архивировать документ."""
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        doc.is_archived = True
        await self.db.flush()

        log = DocumentLog(
            document_id=doc_id,
            user_id=user_id,
            action="ARCHIVED",
            new_value="Document archived",
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(doc)

        return DocumentResponse.model_validate(doc)

    async def unarchive(self, doc_id: int, user_id: int) -> DocumentResponse:
        """Восстановить документ из архива."""
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        doc.is_archived = False
        await self.db.flush()

        log = DocumentLog(
            document_id=doc_id,
            user_id=user_id,
            action="UNARCHIVED",
            new_value="Document unarchived",
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(doc)

        return DocumentResponse.model_validate(doc)

    async def assign_user(self, doc_id: int, user_id_to_assign: int, current_user_id: int) -> DocumentResponse:
        """Назначить пользователя на документ."""
        from app.auth.models import User
        user_result = await self.db.execute(
            select(func.count()).select_from(User).where(User.id == user_id_to_assign)
        )
        if user_result.scalar_one() == 0:
            raise ValueError(f"User {user_id_to_assign} not found")

        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        old_assigned = doc.assigned_to
        doc.assigned_to = user_id_to_assign
        await self.db.flush()

        log = DocumentLog(
            document_id=doc_id,
            user_id=current_user_id,
            action="ASSIGNMENT_CHANGED",
            field_name="assigned_to",
            old_value=str(old_assigned) if old_assigned else None,
            new_value=str(user_id_to_assign),
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(doc)

        return DocumentResponse.model_validate(doc)

    async def lock(self, doc_id:int, user_id: int) -> DocumentResponse:
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")
        doc.is_locked = True
        await self.db.flush()

        log = DocumentLog(
            document_id=doc_id,
            user_id=user_id,
            action="ARCHIVED",
            new_value="Document archived",
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(doc)

        return DocumentResponse.model_validate(doc)

    async def unlock(self, doc_id:int, user_id: int) -> DocumentResponse:
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")
        doc.is_locked = False
        await self.db.flush()

        log = DocumentLog(
            document_id=doc_id,
            user_id=user_id,
            action="ARCHIVED",
            new_value="Document archived",
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(doc)

        return DocumentResponse.model_validate(doc)
