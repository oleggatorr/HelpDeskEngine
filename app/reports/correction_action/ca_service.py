from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.reports.correction_action.ca_models import (
    CorrectionAction,
    CorrectionActionStatus,
)
from app.reports.correction.correction_models import Correction
from app.reports.models import ProblemRegistration, Document, DocumentType
from app.reports.documents.schemas.document import DocumentCreate, DocumentStage
from app.reports.documents.document_public_service import PublicDocumentService
from app.auth.models import User

from app.reports.correction_action.ca_schemas import (
    CorrectionActionCreate,
    CorrectionActionUpdate,
    CorrectionActionResponse,
    CorrectionActionFilter,
    CorrectionActionListResponse,
)


class CorrectionActionService:
    def __init__(self, db: AsyncSession, doc_service: PublicDocumentService):
        self.db = db
        self.doc_service = doc_service

    # =========================================================
    # CREATE
    # =========================================================
    async def create(self, request: CorrectionActionCreate, created_by: int) -> CorrectionActionResponse:
        # 1. Нормализуем FK-поля
        correction_id = request.correction_id or None
        assigned_user_id = request.assigned_user_id or None

        # 2. Получаем doc_type_id
        doc_type_result = await self.db.execute(
            select(DocumentType.id).where(DocumentType.code == "CorrectionAction")
        )
        doc_type_id = doc_type_result.scalar_one_or_none()
        if not doc_type_id:
            raise ValueError("DocumentType 'CorrectionAction' not found in registry")

        # 3. Валидация существующих сущностей
        if correction_id and not await self._exists_by_id(Correction, correction_id):
            raise ValueError("Correction not found")
        if assigned_user_id and not await self._exists_by_id(User, assigned_user_id):
            raise ValueError("Assigned user not found")

        # 4. Создаём документ
        doc = await self.doc_service.create(DocumentCreate(
            created_by=created_by,
            status=request.doc_status or DocumentStatus.OPEN,  # ✅ Валидный статус
            doc_type_id=doc_type_id,
            current_stage=DocumentStage.NEW,
            language=request.doc_language or DocumentLanguage.RU,
            priority=request.doc_priority or DocumentPriority.MEDIUM,
            assigned_to=assigned_user_id,
            # ❌ Убраны: meta, attachment_files (нет в схеме DocumentCreate)
        ))
        document_id = doc.id

        # 5. Создаём действие
        now = datetime.now(timezone.utc)
        action = CorrectionAction(
            correction_id=correction_id,
            document_id=document_id,
            assigned_user_id=assigned_user_id,
            description=request.description,
            status=CorrectionActionStatus.PENDING.value,  # ✅ Строка для БД
            assigned_at=now if assigned_user_id else None,
        )

        # Авто-переход при назначении
        if assigned_user_id:
            action.status = CorrectionActionStatus.IN_PROGRESS.value  # ✅ Строка

        self.db.add(action)
        await self.db.flush()

        await self.db.commit()
        await self.db.refresh(action)

        return await self.get_by_id(action.id)

    # =========================================================
    # GET BY ID
    # =========================================================
    async def get_by_id(self, action_id: int) -> Optional[CorrectionActionResponse]:
        result = await self.db.execute(
            select(CorrectionAction)
            .where(CorrectionAction.id == action_id)
            .options(
                selectinload(CorrectionAction.assignee),
                selectinload(CorrectionAction.correction),
            )
        )
        action = result.scalar_one_or_none()
        return self._to_response(action) if action else None

    # =========================================================
    # GET BY CORRECTION
    # =========================================================
    async def get_by_correction_id(
        self, correction_id: int, filters: Optional[CorrectionActionFilter] = None
    ) -> CorrectionActionListResponse:

        if not await self._exists_by_id(Correction, correction_id):
            raise ValueError("Correction not found")

        filters = filters or CorrectionActionFilter()
        conditions = [CorrectionAction.correction_id == correction_id]
        conditions.extend(self._build_filters(filters))

        query = (
            select(CorrectionAction)
            .where(and_(*conditions))
            .options(selectinload(CorrectionAction.assignee))
        )

        total = await self._count(query)
        query = self._apply_sorting(query, filters).offset(filters.offset).limit(filters.limit)
        rows = (await self.db.execute(query)).scalars().all()

        return CorrectionActionListResponse(
            items=[self._to_response(r) for r in rows],
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    # =========================================================
    # UPDATE
    # =========================================================
    async def update(self, action_id: int, request: CorrectionActionUpdate) -> Optional[CorrectionActionResponse]:
        action = await self._get_model(action_id)
        if not action:
            return None

        data = request.model_dump(exclude_unset=True)

        if "assigned_user_id" in data:
            user_id = data["assigned_user_id"]
            if user_id is not None and not await self._exists_by_id(User, user_id):
                raise ValueError("User not found")
            if user_id != action.assigned_user_id:
                data["assigned_at"] = datetime.now(timezone.utc)
                data["status"] = CorrectionActionStatus.IN_PROGRESS.value  # ✅ Строка

        if "status" in data:
            new_status = data["status"]
            if isinstance(new_status, CorrectionActionStatus):
                new_status = new_status.value
            self._apply_status_transition(action, new_status)

        for field, value in data.items():
            setattr(action, field, value)

        await self.db.commit()
        await self.db.refresh(action)
        return self._to_response(action)

    # =========================================================
    # DELETE
    # =========================================================
    async def delete(self, action_id: int) -> bool:
        action = await self._get_model(action_id)
        if not action:
            return False
        await self.db.delete(action)
        await self.db.commit()
        return True

    # =========================================================
    # GET ALL
    # =========================================================
    async def get_all(self, filters: Optional[CorrectionActionFilter] = None) -> CorrectionActionListResponse:
        filters = filters or CorrectionActionFilter()
        query = select(CorrectionAction).options(
            selectinload(CorrectionAction.assignee),
            selectinload(CorrectionAction.correction),
        )

        conditions = self._build_filters(filters)
        if conditions:
            query = query.where(and_(*conditions))

        total = await self._count(query)
        query = self._apply_sorting(query, filters).offset(filters.offset).limit(filters.limit)
        rows = (await self.db.execute(query)).scalars().all()

        return CorrectionActionListResponse(
            items=[self._to_response(r) for r in rows],
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    # =========================================================
    # 🔧 HELPERS
    # =========================================================
    async def _get_model(self, action_id: int) -> Optional[CorrectionAction]:
        result = await self.db.execute(
            select(CorrectionAction).where(CorrectionAction.id == action_id)
        )
        return result.scalar_one_or_none()

    async def _exists_by_id(self, model, obj_id: int) -> bool:
        result = await self.db.execute(select(1).select_from(model).where(model.id == obj_id).limit(1))
        return result.scalar_one_or_none() is not None

    async def _count(self, query) -> int:
        subq = query.subquery()
        result = await self.db.execute(select(func.count()).select_from(subq))
        return result.scalar_one()

    def _apply_sorting(self, query, filters: CorrectionActionFilter):
        sort_col = getattr(CorrectionAction, filters.sort_by, CorrectionAction.id)
        return query.order_by(sort_col.asc() if filters.sort_order == "asc" else sort_col.desc())

    def _build_filters(self, filters: CorrectionActionFilter):
        conditions = []
        if filters.correction_id is not None:
            conditions.append(CorrectionAction.correction_id == filters.correction_id)
        if filters.document_id is not None:
            conditions.append(CorrectionAction.document_id == filters.document_id)
        if filters.assigned_user_id is not None:
            conditions.append(CorrectionAction.assigned_user_id == filters.assigned_user_id)
        if filters.status is not None:
            # ✅ Сравнение со строковым значением из БД
            val = filters.status.value if hasattr(filters.status, "value") else filters.status
            conditions.append(CorrectionAction.status == val)
        if filters.description:
            conditions.append(CorrectionAction.description.ilike(f"%{filters.description}%"))
        if filters.comment:
            conditions.append(CorrectionAction.comment.ilike(f"%{filters.comment}%"))
        if filters.created_from:
            conditions.append(CorrectionAction.created_at >= filters.created_from)
        if filters.created_to:
            conditions.append(CorrectionAction.created_at <= filters.created_to)
        return conditions

    def _apply_status_transition(self, action: CorrectionAction, new_status: str):
        """Принимает строку статуса, валидирует переходы и обновляет таймстемпы."""
        # Конвертируем строку обратно в Enum для проверки графа переходов
        try:
            new_status_enum = CorrectionActionStatus(new_status)
            current_enum = CorrectionActionStatus(action.status)
        except ValueError:
            raise ValueError(f"Invalid status value: {new_status}")

        valid_transitions = {
            CorrectionActionStatus.PENDING: {CorrectionActionStatus.IN_PROGRESS, CorrectionActionStatus.SKIPPED},
            CorrectionActionStatus.IN_PROGRESS: {CorrectionActionStatus.COMPLETED, CorrectionActionStatus.SKIPPED},
            CorrectionActionStatus.COMPLETED: set(),
            CorrectionActionStatus.SKIPPED: set(),
        }

        if new_status_enum not in valid_transitions[current_enum]:
            raise ValueError(f"Invalid transition: {current_enum.value} → {new_status}")

        now = datetime.now(timezone.utc)
        if new_status_enum == CorrectionActionStatus.IN_PROGRESS:
            action.assigned_at = action.assigned_at or now
        elif new_status_enum == CorrectionActionStatus.COMPLETED:
            if not action.assigned_user_id:
                raise ValueError("Cannot complete action without assignee")
            action.completed_at = now
        elif new_status_enum == CorrectionActionStatus.SKIPPED:
            action.completed_at = None

        action.status = new_status

    def _to_response(self, action: CorrectionAction) -> CorrectionActionResponse:
        """Конвертация ORM-объекта в Pydantic-схему."""
        return CorrectionActionResponse(
            id=action.id,
            correction_id=action.correction_id,
            document_id=action.document_id,
            assigned_user_id=action.assigned_user_id,
            description=action.description,
            # ✅ Явная конвертация строки → Enum для валидации схемой
            status=CorrectionActionStatus(action.status) if isinstance(action.status, str) else action.status,
            comment=action.comment,
            created_at=action.created_at,
            assigned_at=action.assigned_at,
            completed_at=action.completed_at,
            # ⚠️ Если нужны эти поля, добавьте их в CorrectionActionResponse schema:
            # assignee_name=action.assignee.full_name if action.assignee else None,
            # correction_title=action.correction.title if action.correction else None,
        )