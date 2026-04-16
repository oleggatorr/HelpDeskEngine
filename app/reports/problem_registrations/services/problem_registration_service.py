from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.reports.models import ProblemRegistration, Document, DocumentType
from app.reports.problem_registrations.schemas.problem_registration import (
    ProblemRegistrationCreate,
    ProblemRegistrationUpdate,
    ProblemRegistrationResponse,
    ProblemRegistration_DetaleUpdate,
)
from app.reports.documents.schemas.document import DocumentCreate, DocumentStage
from app.reports.documents.public_services.document import PublicDocumentService
from app.messeges.models import Chat, Message, MessageAttachment, chat_participants
from app.auth.models import User


class ProblemRegistrationService:
    """
    Сервис регистраций проблем.
    Использует DocumentService для работы с документами.
    """

    def __init__(self, db: AsyncSession, doc_service: PublicDocumentService):
        self.db = db
        self.doc_service = doc_service

    async def create(self, request: ProblemRegistrationCreate, created_by: int) -> ProblemRegistrationResponse:
        # Нормализуем FK-поля: 0 → None
        location_id = request.location_id or None

        # Получаем doc_type_id из справочника по коду "ProblemRegistration"
        doc_type_result = await self.db.execute(
            select(DocumentType.id).where(DocumentType.code == "ProblemRegistration")
        )
        doc_type_id = doc_type_result.scalar_one_or_none()

        # Проверяем существование FK
        if location_id:
            from app.knowledge_base.models import Location
            result = await self.db.execute(
                select(func.count()).select_from(Location).where(Location.id == location_id)
            )
            if result.scalar_one() == 0:
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
            name=f"Обращение #{doc.track_id} - {request.subject}" ,
            document_id=doc.id,
        )
        # Добавляем создателя как участника
        creator = await self.db.execute(select(User).where(User.id == created_by))
        creator_user = creator.scalar_one_or_none()
        if creator_user:
            chat.participants = [creator_user]
        self.db.add(chat)

        # 4. Отправляем первое сообщение с темой и описанием проблемы
        if request.subject or request.description:
            # Используем flush чтобы получить chat.id до commit
            await self.db.flush()
            first_message = Message(
                chat_id=chat.id,
                sender_id=created_by,
                content=f"<p>{request.subject or '—'}</p>{request.description or '—'}",
            )
            self.db.add(first_message)

            # 5. Копируем вложения документа в сообщение чата
            if getattr(request, 'attachment_files', None):
                await self.db.flush()  # чтобы получить first_message.id
                for att_data in request.attachment_files:
                    message_attachment = MessageAttachment(
                        message_id=first_message.id,
                        file_path=att_data["file_path"],
                        original_filename=att_data.get("original_filename"),
                        file_type=att_data.get("file_type", "application/octet-stream"),
                    )
                    self.db.add(message_attachment)

        await self.db.commit()
        await self.db.refresh(registration)

        # Возвращаем с полями документа (JOIN)
        return await self.get_by_id(registration.id)

    async def get_by_id(self, registration_id: int) -> Optional[ProblemRegistrationResponse]:
        result = await self.db.execute(
            select(ProblemRegistration, Document)
            .join(Document, ProblemRegistration.document_id == Document.id)
            .where(ProblemRegistration.id == registration_id)
        )
        row = result.first()
        if not row:
            return None
        return self._row_to_response(row)

    async def get_by_document_id(self, doc_id: int) -> Optional[ProblemRegistrationResponse]:
        result = await self.db.execute(
            select(ProblemRegistration, Document)
            .join(Document, ProblemRegistration.document_id == Document.id)
            .where(ProblemRegistration.document_id == doc_id)
        )
        row = result.first()
        if not row:
            return None
        return self._row_to_response(row)

    async def get_by_track_id(self, track_id: str) -> Optional[ProblemRegistrationResponse]:
        """Получить регистрацию проблемы по трек-номеру документа."""
        result = await self.db.execute(
            select(ProblemRegistration, Document)
            .join(Document, ProblemRegistration.document_id == Document.id)
            .where(Document.track_id == track_id)
        )
        row = result.first()
        if not row:
            return None
        return self._row_to_response(row)

    async def update(self, registration_id: int, request: ProblemRegistrationUpdate) -> Optional[ProblemRegistrationResponse]:
        """Обновить регистрацию проблемы."""
        from sqlalchemy import select, func
        from app.reports.models import ProblemRegistration
        from app.reports.models import ProblemAction  # Ваш enum
        
        result = await self.db.execute(
            select(ProblemRegistration).where(ProblemRegistration.id == registration_id)
        )
        registration = result.scalar_one_or_none()
        if not registration:
            return None

        update_data = request.model_dump(exclude_unset=True)
        
        if update_data:
            # 🔧 Нормализуем FK-поля: 0 → None
            if "location_id" in update_data and not update_data["location_id"]:
                update_data["location_id"] = None

            # 🔧 Проверяем существование location_id
            if update_data.get("location_id"):
                from app.knowledge_base.models import Location
                loc_result = await self.db.execute(
                    select(func.count()).select_from(Location).where(Location.id == update_data["location_id"])
                )
                if loc_result.scalar_one() == 0:
                    update_data["location_id"] = None

            # 🔥 ГЛАВНОЕ ИСПРАВЛЕНИЕ: пропускаем None для полей с NOT NULL
            for field, value in update_data.items():
                # Для поля action: если None или пустая строка — подставляем дефолт
                if field == "action" and (value is None or value == ""):
                    value = ProblemAction.UNDEFINED.value
                
                # Обновляем только если значение не None (защита от NOT NULL)
                if value is not None:
                    setattr(registration, field, value)
                    
            await self.db.commit()
            await self.db.refresh(registration)

        return await self.get_by_id(registration_id)

    async def delete(self, registration_id: int) -> bool:
        """Удалить регистрацию проблемы (вместе с документом через cascade)."""
        result = await self.db.execute(
            select(ProblemRegistration).where(ProblemRegistration.id == registration_id)
        )
        registration = result.scalar_one_or_none()
        if not registration:
            return False

        await self.db.delete(registration)
        await self.db.commit()
        return True

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[object] = None,
    ) -> dict:
        """Список регистраций с total-счётчиком и фильтрами."""
        from app.reports.models import DocumentStage as DocumentStageEnum

        conditions = []
        print(filters.assigned_to)
        if filters:
            # Фильтры по ProblemRegistration
            if filters.subject:
                conditions.append(ProblemRegistration.subject.ilike(f"%{filters.subject}%"))
            if filters.detected_from:
                conditions.append(ProblemRegistration.detected_at >= filters.detected_from)
            if filters.detected_to:
                conditions.append(ProblemRegistration.detected_at <= filters.detected_to)
            if filters.location_id:
                conditions.append(ProblemRegistration.location_id == filters.location_id)
            if filters.description:
                conditions.append(ProblemRegistration.description.ilike(f"%{filters.description}%"))
            if filters.nomenclature:
                conditions.append(ProblemRegistration.nomenclature.ilike(f"%{filters.nomenclature}%"))
            # Фильтры по Document
            if filters.track_id:
                conditions.append(Document.track_id.ilike(f"%{filters.track_id}%"))
            if filters.doc_created_from:
                conditions.append(Document.created_at >= filters.doc_created_from)
            if filters.doc_created_to:
                conditions.append(Document.created_at <= filters.doc_created_to)
            if filters.doc_status:
                status_value = filters.doc_status.value if hasattr(filters.doc_status, 'value') else filters.doc_status
                conditions.append(Document.status == status_value)
            if filters.doc_type_id:
                conditions.append(Document.doc_type_id == filters.doc_type_id)
            if filters.doc_current_stage:
                try:
                    stage_enum = DocumentStageEnum[filters.doc_current_stage]
                    conditions.append(Document.current_stage == stage_enum)
                except KeyError:
                    pass
            if filters.created_by is not None:
                conditions.append(Document.created_by == filters.created_by)
                
            if filters.assigned_to is not None:
                if filters.assigned_to == -1:
                    # 🔹 Специальное значение -1 → ищем где assigned_to IS NULL
                    conditions.append(Document.assigned_to.is_(None))
                elif filters.assigned_to > 0:
                    # 🔹 Положительное число → ищем по точному ID
                    conditions.append(Document.assigned_to == filters.assigned_to)
                # Если 0 или отрицательное (кроме -1) — игнорируем фильтр

        # Базовый запрос с JOIN
        query_base = select(ProblemRegistration, Document).join(
            Document, ProblemRegistration.document_id == Document.id
        )
        if conditions:
            from sqlalchemy import and_
            query_base = query_base.where(and_(*conditions))

        # Счётчик
        count_query = select(func.count()).select_from(query_base.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Сортировка
        sort_col = getattr(ProblemRegistration, filters.sort_by if filters else "id", ProblemRegistration.id)
        order_fn = sort_col.asc if (filters and filters.sort_order == "asc") else sort_col.desc
        query = query_base.order_by(order_fn()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()
        items = [self._row_to_response(row) for row in rows]

        return {"items": items, "total": total}

    def _row_to_response(self, row) -> ProblemRegistrationResponse:
        """Конвертация строки (registration, document) в Response."""
        from app.reports.models import DocumentStage as DocumentStageEnum

        reg, doc = row
        stage = doc.current_stage

        # Нормализуем stage в строку
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
        )
    

    async def update_response_details(
        self, 
        registration_id: int, 
        request: ProblemRegistration_DetaleUpdate
    ) -> Optional[ProblemRegistrationResponse]:
        """Обновить дополнительную информацию/обработку регистрации проблемы."""
        result = await self.db.execute(
            select(ProblemRegistration).where(ProblemRegistration.id == registration_id)
        )
        registration = result.scalar_one_or_none()
        if not registration:
            return None

        update_data = request.model_dump(exclude_unset=True)
        if update_data:
            # 1. Нормализуем FK: 0 или пустое значение → None
            if "responsible_department_id" in update_data and not update_data["responsible_department_id"]:
                update_data["responsible_department_id"] = None

            # 2. (Опционально) Проверка существования department_id
            if update_data.get("responsible_department_id"):
                from app.knowledge_base.models import Department  # замените на ваш реальный путь
                dept_exists = await self.db.execute(
                    select(func.count()).select_from(Department).where(
                        Department.id == update_data["responsible_department_id"]
                    )
                )
                if dept_exists.scalar_one() == 0:
                    update_data["responsible_department_id"] = None

            # 3. Безопасное применение полей
            for field, value in update_data.items():
                # Если action приходит как Enum, а в БД колонка String/Integer
                if field == "action" and hasattr(value, "value"):
                    value = value.value
                setattr(registration, field, value)

            await self.db.commit()
            await self.db.refresh(registration)

        return await self.get_by_id(registration_id)
    

    async def archive_document(self, doc_id: int, user_id: int) -> ProblemRegistrationResponse:
        """Архивировать документ и регистрацию."""
        return await self.doc_service.archive(doc_id, user_id)

    async def unarchive_document(self, doc_id: int, user_id: int) -> ProblemRegistrationResponse:
        """Восстановить документ и регистрацию из архива."""
        return await self.doc_service.unarchive(doc_id, user_id)

    async def assign_user_to_document(self, doc_id: int, user_id: int, current_user_id: int) -> ProblemRegistrationResponse:
        """Назначить пользователя на документ."""
        return await self.doc_service.assign_to_user(doc_id, user_id, current_user_id)
    

