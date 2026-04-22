# app/correction/services.py
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.reports.correction.models import Correction, CorrectionStatus
from app.reports.models import ProblemRegistration, Document, DocumentType
from app.reports.correction.schemas.correction import (
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
    """
    Сервис корректирующих действий.
    Работает в связке с DocumentService для синхронизации статусов и аудита.
    """

    # 🔒 Whitelist для безопасной сортировки
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

    # ==========================================
    # 🆕 CREATE
    # ==========================================
    async def create(self, request: CorrectionCreate, created_by: int) -> CorrectionResponse:
        # 🔍 1. Проверка существования заявки
        pr_check = await self.db.execute(
            select(func.count()).select_from(ProblemRegistration).where(
                ProblemRegistration.id == request.problem_registration_id
            )
        )
        if pr_check.scalar_one() == 0:
            raise HTTPException(status_code=404, detail="ProblemRegistration not found")

        # 📄 2. Получаем doc_type_id
        doc_type_result = await self.db.execute(
            select(DocumentType.id).where(DocumentType.code == "CorrectiveAction")
        )
        doc_type_id = doc_type_result.scalar_one_or_none()

        # 🆕 3. Создаём документ автоматически
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

        # 🛠 4. Создаём запись коррекции
        correction = Correction(
            document_id=doc.id,
            problem_registration_id=request.problem_registration_id,
            title=request.title,
            description=request.description,
            corrective_action=request.corrective_action,
            status=request.status,
            planned_date=request.planned_date,
            completed_date=request.completed_date,
            created_by=created_by,
        )
        self.db.add(correction)

        # 💬 5. Чат + стартовое сообщение
        chat = Chat(
            name=f"Коррекция #{doc.track_id} - {request.title}",
            document_id=doc.id,
        )
        creator = await self.db.execute(select(User).where(User.id == created_by))
        creator_user = creator.scalar_one_or_none()
        if creator_user:
            chat.participants = [creator_user]
        self.db.add(chat)

        if request.title or request.corrective_action:
            await self.db.flush()
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

            if request.attachment_files:
                await self.db.flush()
                for att in request.attachment_files:
                    self.db.add(MessageAttachment(
                        message_id=first_msg.id,
                        file_path=att["file_path"],
                        original_filename=att.get("original_filename"),
                        file_type=att.get("file_type", "application/octet-stream"),
                    ))

        await self.db.commit()
        await self.db.refresh(correction)
        return await self.get_by_id(correction.id)

    # ==========================================
    # 🔍 READ (GET)
    # ==========================================
    async def get_by_id(self, correction_id: int) -> Optional[CorrectionResponse]:
        return await self._get_correction_row(Correction.id == correction_id)

    async def get_by_document_id(self, doc_id: int) -> Optional[CorrectionResponse]:
        return await self._get_correction_row(Correction.document_id == doc_id)

    async def get_by_track_id(self, track_id: str) -> Optional[CorrectionResponse]:
        return await self._get_correction_row(Document.track_id == track_id)

    async def get_by_problem_registration_id(self, pr_id: int) -> Optional[CorrectionResponse]:
        return await self._get_correction_row(Correction.problem_registration_id == pr_id)

    async def _get_correction_row(self, where_clause) -> Optional[CorrectionResponse]:
        """Внутренний универсальный поиск с JOIN и load-опциями."""
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
        return self._row_to_response(row) if row else None

    # ==========================================
    # 📝 UPDATE
    # ==========================================
    async def update(self, correction_id: int, request: CorrectionUpdate) -> Optional[CorrectionResponse]:
        result = await self.db.execute(select(Correction).where(Correction.id == correction_id))
        correction = result.scalar_one_or_none()
        if not correction:
            return None

        update_data = request.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(correction_id)

        # 🔒 FK не меняем постфактум
        update_data.pop("document_id", None)
        update_data.pop("problem_registration_id", None)

        for field, value in list(update_data.items()):
            # 🔄 Status → строка, дефолт при пустоте
            if field == "status":
                if value is None or value == "":
                    value = CorrectionStatus.PLANNED.value
                elif hasattr(value, "value"):
                    value = value.value

            # 📝 NOT NULL поля → игнорируем явный None/""
            if field in ("title", "corrective_action") and (value is None or value == ""):
                update_data.pop(field)
                continue

            # 👥 Валидация FK пользователей
            if field in ("completed_by", "verified_by") and value is not None:
                user_check = await self.db.execute(
                    select(func.count()).select_from(User).where(User.id == value)
                )
                if user_check.scalar_one() == 0:
                    update_data.pop(field)
                    continue

        for field, value in update_data.items():
            setattr(correction, field, value)

        await self.db.commit()
        await self.db.refresh(correction)
        return await self.get_by_id(correction_id)

    # ==========================================
    # 🗑 DELETE (Soft)
    # ==========================================
    async def delete(self, correction_id: int) -> bool:
        result = await self.db.execute(select(Correction).where(Correction.id == correction_id))
        correction = result.scalar_one_or_none()
        if not correction or correction.is_deleted:
            return False

        correction.is_deleted = True
        await self.db.commit()
        return True

    # ==========================================
    # 📊 GET ALL (LIST + FILTER + PAGINATION)
    # ==========================================
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[CorrectionFilter] = None,
    ) -> dict:
        conditions = []

        if filters:
            # Correction фильтры
            if filters.title:
                conditions.append(Correction.title.ilike(f"%{filters.title}%"))
            if filters.description:
                conditions.append(Correction.description.ilike(f"%{filters.description}%"))
            if filters.status is not None:
                conditions.append(Correction.status == (filters.status.value if hasattr(filters.status, "value") else filters.status))
            if filters.planned_date_from:
                conditions.append(Correction.planned_date >= filters.planned_date_from)
            if filters.planned_date_to:
                conditions.append(Correction.planned_date <= filters.planned_date_to)

            # Document фильтры
            if filters.track_id:
                conditions.append(Document.track_id.ilike(f"%{filters.track_id}%"))
            if filters.doc_created_from:
                conditions.append(Document.created_at >= filters.doc_created_from)
            if filters.doc_created_to:
                conditions.append(Document.created_at <= filters.doc_created_to)
            if filters.doc_status is not None:
                conditions.append(Document.status == (filters.doc_status.value if hasattr(filters.doc_status, "value") else filters.doc_status))
            if filters.doc_type_id is not None:
                conditions.append(Document.doc_type_id == filters.doc_type_id)
            if filters.doc_current_stage:
                conditions.append(Document.current_stage == filters.doc_current_stage)
            if filters.created_by is not None:
                conditions.append(Document.created_by == filters.created_by)
            if filters.assigned_to is not None:
                conditions.append(Document.assigned_to.is_(None) if filters.assigned_to == -1 else Document.assigned_to == filters.assigned_to)
            if filters.is_locked is not None:
                conditions.append(Document.is_locked == filters.is_locked)

        base_query = select(Correction, Document).join(
            Document, Correction.document_id == Document.id
        )
        if conditions:
            base_query = base_query.where(and_(*conditions))

        # 🔢 Count (отдельно, без options)
        count_stmt = select(func.count(Correction.id)).join(
            Document, Correction.document_id == Document.id
        ).where(and_(*conditions)) if conditions else select(func.count(Correction.id))
        total = (await self.db.execute(count_stmt)).scalar_one()

        # ↕️ Сортировка (безопасная)
        sort_by = (filters.sort_by or "id") if filters else "id"
        sort_order = ((filters.sort_order or "desc").lower()) if filters else "desc"
        sort_col = self._SORT_COLUMNS.get(sort_by, Correction.id)
        order_fn = sort_col.asc if sort_order == "asc" else sort_col.desc

        final_query = (
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

        result = await self.db.execute(final_query)
        rows = result.all()
        items = [self._row_to_response(row) for row in rows]

        return {"items": items, "total": total}

    # ==========================================
    # 🔄 HELPER: Row → Response
    # ==========================================
    def _row_to_response(self, row) -> CorrectionResponse:
        corr, doc = row

        def _get_enum_val(obj):
            return obj.value if hasattr(obj, "value") else obj

        return CorrectionResponse(
            id=corr.id,
            document_id=corr.document_id,
            problem_registration_id=corr.problem_registration_id,
            title=corr.title,
            description=corr.description,
            corrective_action=corr.corrective_action,
            status=_get_enum_val(corr.status),
            planned_date=corr.planned_date,
            completed_date=corr.completed_date,
            created_at=corr.created_at,
            updated_at=corr.updated_at,
            is_deleted=corr.is_deleted,
            created_by=corr.created_by,
            completed_by=corr.completed_by,
            verified_by=corr.verified_by,
            track_id=doc.track_id,
            doc_created_at=doc.created_at,
            doc_current_stage=_get_enum_val(doc.current_stage),
            doc_status=_get_enum_val(doc.status),
            is_locked=doc.is_locked,
            is_archived=doc.is_archived,
            assigned_to=doc.assigned_to,
        )

    # ==========================================
    # 📦 DOCUMENT DELEGATION
    # ==========================================
    async def archive_document(self, doc_id: int, user_id: int) -> CorrectionResponse:
        return await self.doc_service.archive(doc_id, user_id)

    async def unarchive_document(self, doc_id: int, user_id: int) -> CorrectionResponse:
        return await self.doc_service.unarchive(doc_id, user_id)

    async def assign_user_to_document(self, doc_id: int, user_id: int, current_user_id: int) -> CorrectionResponse:
        return await self.doc_service.assign_to_user(doc_id, user_id, current_user_id)