from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import select, func

from app.reports.models import Document, DocumentType
from app.reports.models import DocumentStage
from app.auth.models import User
from app.reports.documents.schemas.document import (
    DocumentCreate, DocumentResponse, DocumentListResponse, DocumentUpdate,
    DocumentFilter,
    generate_track_id,
)
from fastapi import HTTPException


class AdminDocumentService:
    """Сервис админки для документов."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _to_response(self, doc: Document) -> DocumentResponse:
        return DocumentResponse(
            id=doc.id,
            track_id=doc.track_id,
            created_at=doc.created_at,
            created_by=doc.created_by,
            status=doc.status,
            doc_type_id=doc.doc_type_id,
            current_stage=doc.current_stage.name if doc.current_stage else DocumentStage.NEW.name,
        )

    async def list_documents(
        self,
        filters: Optional[DocumentFilter] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentListResponse:
        conditions = []

        if filters:
            if filters.track_id:
                conditions.append(Document.track_id.ilike(f"%{filters.track_id}%"))
            if filters.created_by is not None:
                conditions.append(Document.created_by == filters.created_by)
            if filters.status is not None:
                status_value = filters.status.value if hasattr(filters.status, 'value') else filters.status
                conditions.append(Document.status == status_value)
            if filters.doc_type_id is not None:
                conditions.append(Document.doc_type_id == filters.doc_type_id)
            if filters.current_stage is not None:
                conditions.append(Document.current_stage == filters.current_stage)
            if filters.created_from is not None:
                conditions.append(Document.created_at >= filters.created_from)
            if filters.created_to is not None:
                conditions.append(Document.created_at <= filters.created_to)

        query_base = select(Document)
        if conditions:
            from sqlalchemy import and_
            query_base = query_base.where(and_(*conditions))

        # Подсчёт
        count_query = select(func.count()).select_from(query_base.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Сортировка
        sort_col = getattr(Document, filters.sort_by) if filters and filters.sort_by else Document.id
        order_fn = sort_col.asc if (filters and filters.sort_order == "asc") else sort_col.desc

        # Пагинация
        result = await self.db.execute(
            query_base.order_by(order_fn()).offset(skip).limit(limit)
        )
        items = result.scalars().all()

        return DocumentListResponse(
            documents=[self._to_response(d) for d in items],
            total=total,
        )

    async def get_document(self, doc_id: int) -> Optional[DocumentResponse]:
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        return self._to_response(doc) if doc else None

    async def get_by_track_id(self, track_id: str) -> Optional[DocumentResponse]:
        """Получение документа по трек-номеру."""
        result = await self.db.execute(
            select(Document).where(Document.track_id == track_id)
        )
        doc = result.scalar_one_or_none()
        return self._to_response(doc) if doc else None

    async def create_document(self, data: DocumentCreate) -> DocumentResponse:
        # Генерация уникального track_id
        track_id = data.track_id
        if not track_id:
            # Генерируем и проверяем на уникальность
            for _ in range(10):
                track_id = generate_track_id()
                result = await self.db.execute(
                    select(func.count()).select_from(Document).where(Document.track_id == track_id)
                )
                if not result.scalar_one():
                    break
            else:
                raise HTTPException(status_code=500, detail="Не удалось сгенерировать уникальный track_id")

        # Проверка FK
        if data.created_by:
            result = await self.db.execute(select(func.count()).select_from(User).where(User.id == data.created_by))
            if not result.scalar_one():
                raise HTTPException(status_code=400, detail=f"Пользователь created_by={data.created_by} не найден")

        if data.doc_type_id:
            result = await self.db.execute(select(func.count()).select_from(DocumentType).where(DocumentType.id == data.doc_type_id))
            if not result.scalar_one():
                raise HTTPException(status_code=400, detail=f"Тип документа doc_type_id={data.doc_type_id} не найден")

        doc = Document(
            track_id=track_id,
            created_by=data.created_by if data.created_by else None,
            status=data.status if data.status else None,
            doc_type_id=data.doc_type_id if data.doc_type_id else None,
            current_stage=data.current_stage or DocumentStage.NEW,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        return DocumentResponse(
            id=doc.id,
            track_id=doc.track_id,
            created_at=doc.created_at,
            created_by=doc.created_by,
            status=doc.status,
            doc_type_id=doc.doc_type_id,
            current_stage=doc.current_stage.name if doc.current_stage else DocumentStage.NEW.name,
        )

    async def update_document(
        self, doc_id: int, data: DocumentUpdate
    ) -> Optional[DocumentResponse]:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_document(doc_id)

        from sqlalchemy import update as sa_update
        await self.db.execute(
            sa_update(Document).where(Document.id == doc_id).values(**update_data)
        )
        await self.db.commit()
        return await self.get_document(doc_id)

    async def delete_document(self, doc_id: int) -> bool:

        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return False

        await self.db.delete(doc)
        await self.db.commit()
        return True
