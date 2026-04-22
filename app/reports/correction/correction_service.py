# app/correction/services.py
from typing import Optional, List, Dict
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.reports.correction.models import Correction, CorrectionStatus
from app.reports.correction.schemas.correction import (
    CorrectionCreate, 
    CorrectionUpdate, 
    CorrectionResponse, 
    CorrectionFilter
)
from app.reports.documents.models import Document
from app.reports.problem_registrations.models import ProblemRegistration

from app.auth.models import User
# Замените на актуальный путь к вашему сервису документов
from app.reports.documents.document_public_service import PublicDocumentService  
from app.reports.correction.models import CorrectionStatus


class CorrectionService:
    """
    Сервис корректирующих действий.
    Работает в связке с DocumentService для синхронизации статусов и аудита.
    """

    def __init__(self, db: AsyncSession, doc_service: PublicDocumentService):
        self.db = db
        self.doc_service = doc_service

    async def create(self, request: CorrectionCreate, created_by: int) -> CorrectionResponse:
        """Создание коррекции с валидацией связей и 1:1 уникальности."""
        # 1. Проверка Document
        doc_res = await self.db.execute(select(Document).where(Document.id == request.document_id))
        doc = doc_res.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # 2. Проверка ProblemRegistration
        prob_res = await self.db.execute(
            select(ProblemRegistration).where(ProblemRegistration.id == request.problem_registration_id)
        )
        prob = prob_res.scalar_one_or_none()
        if not prob:
            raise HTTPException(status_code=404, detail="ProblemRegistration not found")
        if prob.document_id != request.document_id:
            raise HTTPException(status_code=400, detail="Problem не принадлежит указанному Document")

        # 3. Проверка 1:1 (только одна активная коррекция на проблему)
        exists = await self.db.execute(
            select(Correction).where(
                Correction.problem_registration_id == request.problem_registration_id,
                Correction.is_deleted == False
            )
        )
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Активная коррекция уже существует для этой проблемы")

        # 4. Создание
        correction = Correction(
            document_id=request.document_id,
            problem_registration_id=request.problem_registration_id,
            title=request.title,
            description=request.description,
            corrective_action=request.corrective_action,
            status=request.status or CorrectionStatus.PLANNED,
            planned_date=request.planned_date,
            created_by=created_by
        )
        self.db.add(correction)
        await self.db.commit()
        await self.db.refresh(correction)

        # Опционально: синхронизируем статус документа
        # await self.doc_service.update_status(correction.document_id, DocumentStatus.IN_PROGRESS, current_user.id)

        return await self.get_by_id(correction.id)

    async def get_by_id(self, correction_id: int) -> Optional[CorrectionResponse]:
        """Получение по ID с загрузкой связей."""
        result = await self.db.execute(
            select(Correction, Document, ProblemRegistration)
            .join(Document, Correction.document_id == Document.id)
            .join(ProblemRegistration, Correction.problem_registration_id == ProblemRegistration.id)
            .where(Correction.id == correction_id, Correction.is_deleted == False)
            .options(
                selectinload(Correction.creator),
                selectinload(Correction.completer),
                selectinload(Correction.verifier),
            )
        )
        row = result.first()
        return self._row_to_response(row) if row else None

    async def get_by_document_id(self, doc_id: int) -> List[CorrectionResponse]:
        """Список коррекций по документу (если разрешено >1 на документ)."""
        result = await self.db.execute(
            select(Correction, Document, ProblemRegistration)
            .join(Document, Correction.document_id == Document.id)
            .join(ProblemRegistration, Correction.problem_registration_id == ProblemRegistration.id)
            .where(Correction.document_id == doc_id, Correction.is_deleted == False)
            .options(
                selectinload(Correction.creator),
                selectinload(Correction.completer),
                selectinload(Correction.verifier),
            )
        )
        return [self._row_to_response(row) for row in result.all()]

    async def update(self, correction_id: int, request: CorrectionUpdate, current_user: User) -> Optional[CorrectionResponse]:
        """Частичное обновление с валидацией статусных переходов и авто-аудитом."""
        result = await self.db.execute(
            select(Correction).where(Correction.id == correction_id, Correction.is_deleted == False)
        )
        correction = result.scalar_one_or_none()
        if not correction:
            return None

        update_data = request.model_dump(exclude_unset=True)
        now = datetime.now(timezone.utc)

        # 🔒 Валидация перехода статуса
        if "status" in update_data:
            new_status = CorrectionStatus(update_data["status"])
            self._validate_transition(correction.status, new_status)

            if new_status == CorrectionStatus.COMPLETED and not correction.completed_date:
                correction.completed_date = now
                correction.completed_by = current_user.id
            elif new_status == CorrectionStatus.VERIFIED:
                correction.verified_by = current_user.id

            correction.status = new_status
            del update_data["status"]

        # Применение остальных полей
        for field, value in update_data.items():
            setattr(correction, field, value)

        await self.db.commit()
        await self.db.refresh(correction)
        return await self.get_by_id(correction.id)

    async def delete(self, correction_id: int) -> bool:
        """Soft-delete: помечает запись как удалённую. Сохраняет историю для аудита."""
        result = await self.db.execute(
            select(Correction).where(Correction.id == correction_id, Correction.is_deleted == False)
        )
        correction = result.scalar_one_or_none()
        if not correction:
            return False
        
        correction.is_deleted = True
        await self.db.commit()
        return True

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[CorrectionFilter] = None,
    ) -> dict:
        """Список с фильтрацией, пагинацией и сортировкой."""
        conditions = [Correction.is_deleted == False]

        if filters:
            if filters.title:
                conditions.append(Correction.title.ilike(f"%{filters.title}%"))
            if filters.status:
                conditions.append(Correction.status == filters.status)
            if filters.document_id:
                conditions.append(Correction.document_id == filters.document_id)
            if filters.problem_registration_id:
                conditions.append(Correction.problem_registration_id == filters.problem_registration_id)
            if filters.created_by:
                conditions.append(Correction.created_by == filters.created_by)
            if filters.created_from:
                conditions.append(Correction.created_at >= filters.created_from)
            if filters.created_to:
                conditions.append(Correction.created_at <= filters.created_to)
            
            # 🔹 Фильтры по родительскому документу (через JOIN)
            if filters.doc_track_id:
                conditions.append(Document.track_id.ilike(f"%{filters.doc_track_id}%"))
            if filters.doc_status:
                conditions.append(Document.status == filters.doc_status)

        # 📦 Базовый запрос с JOIN
        base_query = (
            select(Correction, Document, ProblemRegistration)
            .join(Document, Correction.document_id == Document.id)
            .join(ProblemRegistration, Correction.problem_registration_id == ProblemRegistration.id)
            .options(
                selectinload(Correction.creator),
                selectinload(Correction.completer),
                selectinload(Correction.verifier),
            )
        )

        if conditions:
            base_query = base_query.where(and_(*conditions))

        # 🔢 Подсчёт общего количества (аналогично вашему примеру)
        count_subq = base_query.subquery()
        count_query = select(func.count()).select_from(count_subq)
        total = (await self.db.execute(count_query)).scalar_one()

        # ↕️ Сортировка
        sort_by = filters.sort_by if filters and filters.sort_by else "created_at"
        sort_order = (filters.sort_order if filters and filters.sort_order else "desc").lower()

        sort_col = getattr(Correction, sort_by, None) or getattr(Document, sort_by, Correction.created_at)
        order_fn = sort_col.asc if sort_order == "asc" else sort_col.desc

        final_query = base_query.order_by(order_fn()).offset(skip).limit(limit)
        result = await self.db.execute(final_query)
        rows = result.all()
        items = [self._row_to_response(row) for row in rows]

        return {"items": items, "total": total}

    def _row_to_response(self, row) -> CorrectionResponse:
        """Конвертация строки (correction, document, problem) в Response."""
        corr, doc, prob = row

        # Безопасное извлечение значений Enum
        status_val = corr.status.value if hasattr(corr.status, 'value') else corr.status
        doc_status_val = doc.status.value if hasattr(doc.status, 'value') else doc.status
        doc_stage_val = doc.current_stage.value if hasattr(doc.current_stage, 'value') else doc.current_stage

        return CorrectionResponse(
            id=corr.id,
            document_id=corr.document_id,
            problem_registration_id=corr.problem_registration_id,
            track_id=doc.track_id,
            title=corr.title,
            description=corr.description,
            corrective_action=corr.corrective_action,
            status=status_val,
            planned_date=corr.planned_date,
            completed_date=corr.completed_date,
            created_at=corr.created_at,
            updated_at=corr.updated_at,
            is_deleted=corr.is_deleted,
            
            # 🔥 Удобные поля для фронтенда
            creator_id=corr.created_by,
            creator_name=corr.creator.username if corr.creator else None,
            completer_id=corr.completed_by,
            completer_name=corr.completer.username if corr.completer else None,
            verifier_id=corr.verified_by,
            verifier_name=corr.verifier.username if corr.verifier else None,
            
            doc_status=doc_status_val,
            doc_stage=doc_stage_val,
            problem_subject=prob.subject,
        )

    @staticmethod
    def _validate_transition(current: CorrectionStatus, target: CorrectionStatus) -> None:
        """Проверка допустимости перехода статуса."""
        allowed = ALLOWED_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Переход из {current.value} в {target.value} запрещён регламентом."
            )