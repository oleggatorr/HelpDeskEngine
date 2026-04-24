from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.reports.models import (
    Document,
    DocumentLog,
    DocumentType,
    DocumentAttachment
)
from app.reports.documents.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
    DocumentStage,
    generate_track_id,
)

from app.reports.enums import (
    DocumentStatus,
    DocumentLanguage,
    DocumentPriority
)


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ===================== HELPERS =====================

    async def _exists(self, model, condition) -> bool:
        result = await self.db.execute(
            select(func.count()).select_from(model).where(condition)
        )
        return result.scalar_one() > 0

    def _normalize_enum(self, value, enum_class):
        if value is None:
            return None
        if isinstance(value, enum_class):
            return value
        return enum_class(value)

    async def _get_or_fail(self, doc_id: int) -> Document:
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")
        return doc

    async def _log(
        self,
        doc_id: int,
        user_id: Optional[int],
        action: str,
        field_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
    ):
        """Добавляет лог в сессию. Фактическая запись произойдёт при коммите."""
        self.db.add(
            DocumentLog(
                document_id=doc_id,
                user_id=user_id,
                action=action,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
            )
        )

    # ===================== CREATE =====================

    async def create(self, request: DocumentCreate) -> DocumentResponse:
        from app.auth.models import User

        track_id = request.track_id or generate_track_id()

        # doc_type
        doc_type_id = request.doc_type_id
        if not doc_type_id:
            result = await self.db.execute(
                select(DocumentType.id).where(DocumentType.code == "Empty")
            )
            doc_type_id = result.scalar_one_or_none()
        else:
            if not await self._exists(DocumentType, DocumentType.id == doc_type_id):
                doc_type_id = None

        # created_by
        created_by = None
        if request.created_by:
            if await self._exists(User, User.id == request.created_by):
                created_by = request.created_by

        doc = Document(
            track_id=track_id,
            created_by=created_by,
            status=self._normalize_enum(request.status, DocumentStatus),
            doc_type_id=doc_type_id,
            current_stage=self._normalize_enum(request.current_stage, DocumentStage),
            is_locked=request.is_locked,
            is_archived=request.is_archived,
            is_anonymized=request.is_anonymized,
            language=self._normalize_enum(request.language, DocumentLanguage),
            priority=self._normalize_enum(request.priority, DocumentPriority),
            assigned_to=request.assigned_to or None,
        )

        self.db.add(doc)
        await self.db.flush()  # ← Получаем doc.id до коммита

        # attachments
        if getattr(request, "attachment_files", None):
            for att in request.attachment_files:
                self.db.add(
                    DocumentAttachment(
                        document_id=doc.id,
                        file_path=att["file_path"],
                        original_filename=att.get("original_filename"),
                        file_type=att.get("file_type", "application/octet-stream"),
                        uploaded_by=created_by,
                    )
                )

        await self._log(
            doc.id,
            created_by,
            "CREATED",
            new_value=f"Document {doc.track_id} created",
        )

        # ❌ commit() делает get_db, не сервис
        await self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    # ===================== READ =====================

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
            skip=skip,
            limit=limit,
            doc_type_id=doc_type_id,
            status=status,
            current_stage=current_stage,
            created_by=created_by,
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

        if track_id:
            conditions.append(Document.track_id.ilike(f"%{track_id}%"))
        if status:
            conditions.append(Document.status == self._normalize_enum(status, DocumentStatus))
        if doc_type_id:
            conditions.append(Document.doc_type_id == doc_type_id)
        if current_stage:
            conditions.append(Document.current_stage == current_stage)
        if is_locked is not None:
            conditions.append(Document.is_locked == is_locked)
        if is_archived is not None:
            conditions.append(Document.is_archived == is_archived)
        if is_anonymized is not None:
            conditions.append(Document.is_anonymized == is_anonymized)
        if language:
            conditions.append(Document.language == self._normalize_enum(language, DocumentLanguage))
        if priority:
            conditions.append(Document.priority == self._normalize_enum(priority, DocumentPriority))
        if created_by:
            conditions.append(Document.created_by == created_by)
        if assigned_to:
            conditions.append(Document.assigned_to == assigned_to)
        if created_from:
            conditions.append(Document.created_at >= created_from)
        if created_to:
            conditions.append(Document.created_at <= created_to)

        query = select(Document)

        if conditions:
            query = query.where(and_(*conditions))

        # count
        total_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar()

        # sorting
        sort_col = getattr(Document, sort_by, Document.id)
        order_fn = sort_col.asc if sort_order == "asc" else sort_col.desc

        query = query.order_by(order_fn()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        docs = result.scalars().all()

        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(d) for d in docs],
            total=total,
        )

    # ===================== UPDATE =====================

    async def update(self, doc_id: int, request, user_id: int) -> DocumentResponse:
        from app.auth.models import User

        doc = await self._get_or_fail(doc_id)

        if doc.is_locked:
            raise ValueError("Document is locked")

        update_data = request.model_dump(exclude_unset=True)

        if "assigned_to" in update_data and update_data["assigned_to"]:
            if not await self._exists(User, User.id == update_data["assigned_to"]):
                raise ValueError(f"User {update_data['assigned_to']} not found")

        enum_fields = {
            "status": DocumentStatus,
            "language": DocumentLanguage,
            "priority": DocumentPriority,
            "current_stage": DocumentStage,
        }

        for field, value in update_data.items():
            if field in enum_fields:
                value = self._normalize_enum(value, enum_fields[field])
            if field in ("doc_type_id", "assigned_to") and not value:
                value = None
            setattr(doc, field, value)

        await self.db.flush()

        await self._log(
            doc_id,
            user_id,
            "UPDATED",
            new_value=f"Fields updated: {', '.join(update_data.keys())}",
        )

        await self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    async def update_stage(
        self, doc_id: int, stage: DocumentStage, user_id: int
    ) -> DocumentResponse:

        doc = await self._get_or_fail(doc_id)

        old_stage = str(doc.current_stage)

        doc.current_stage = stage
        await self.db.flush()

        await self._log(
            doc_id,
            user_id,
            "STAGE_CHANGED",
            field_name="current_stage",
            old_value=old_stage,
            new_value=str(stage),
        )

        await self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    # ===================== DELETE =====================

    async def delete(self, doc_id: int) -> bool:
        doc = await self._get_or_fail(doc_id)
        await self.db.delete(doc)
        # ❌ commit() делает get_db, не сервис
        return True

    # ===================== EXTRA =====================

    async def assign_user(
        self, doc_id: int, user_id_to_assign: int, current_user_id: int
    ) -> DocumentResponse:
        from app.auth.models import User

        if not await self._exists(User, User.id == user_id_to_assign):
            raise ValueError(f"User {user_id_to_assign} not found")

        doc = await self._get_or_fail(doc_id)

        old = doc.assigned_to
        doc.assigned_to = user_id_to_assign

        await self._log(
            doc_id,
            current_user_id,
            "ASSIGNMENT_CHANGED",
            field_name="assigned_to",
            old_value=str(old) if old else None,
            new_value=str(user_id_to_assign),
        )

        await self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    async def archive(self, doc_id: int, user_id: int) -> DocumentResponse:
        doc = await self._get_or_fail(doc_id)
        doc.is_archived = True
        await self._log(doc_id, user_id, "ARCHIVED")
        await self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    async def unarchive(self, doc_id: int, user_id: int) -> DocumentResponse:
        doc = await self._get_or_fail(doc_id)
        doc.is_archived = False
        await self._log(doc_id, user_id, "UNARCHIVED")
        await self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    async def lock(self, doc_id: int, user_id: int) -> DocumentResponse:
        doc = await self._get_or_fail(doc_id)
        doc.is_locked = True
        await self._log(doc_id, user_id, "LOCKED")
        await self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    async def unlock(self, doc_id: int, user_id: int) -> DocumentResponse:
        doc = await self._get_or_fail(doc_id)
        doc.is_locked = False
        await self._log(doc_id, user_id, "UNLOCKED")
        await self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    async def anonymize(self, doc_id: int, user_id: int) -> DocumentResponse:
        from app.messages.models import Chat

        doc = await self._get_or_fail(doc_id)
        doc.is_anonymized = True

        chats_result = await self.db.execute(
            select(Chat).where(Chat.document_id == doc_id)
        )
        chats = chats_result.scalars().all()

        for chat in chats:
            chat.is_anonymized = True

        await self._log(
            doc_id,
            user_id,
            "ANONYMIZED",
            new_value="Document anonymized (chats anonymized too)",
        )

        await self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    async def get_logs(
        self, doc_id: int, skip: int = 0, limit: int = 100
    ) -> List[dict]:

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