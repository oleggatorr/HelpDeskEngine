# app/reports/correction/correction_public_services.py
# from typing import Optional, List
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select  # 🔹 Добавлено
# from datetime import datetime, timezone
# from fastapi import HTTPException, status  # 🔹 Добавлено

# from app.reports.correction.correction_service import CorrectionService
# from app.reports.documents.document_public_service import PublicDocumentService
# from app.reports.correction.schemas.correction import (
#     CorrectionCreate,
#     CorrectionUpdate,
#     CorrectionResponse,
#     CorrectionListResponse,
#     CorrectionFilter,
# )
# from app.reports.correction.models import CorrectionStatus
# from app.auth.models import User  # 🔹 Добавлено


# app/reports/correction/correction_public_service.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.reports.correction.correction_service import CorrectionService
from app.reports.documents.document_public_service import PublicDocumentService
from app.reports.correction.correction_schemas import (
    CorrectionCreate,
    CorrectionUpdate,
    CorrectionResponse,
    CorrectionListResponse,  # ✅ Исправлено: Responce -> Response
    CorrectionFilter,
    CorrectionStatus,
)

class PublicCorrectionService:
    """Публичный слой корректирующих действий."""

    def __init__(self, db: AsyncSession):
        doc_service = PublicDocumentService(db)
        self._service = CorrectionService(db, doc_service)

    async def _send_chat_notification(self, document_id: int, message: str):
        """Отправить системное уведомление в чат документа."""
        from app.messages.public_services import PublicChatService, PublicMessageService
        chat_service = PublicChatService(self._service.db)
        chat_id = await chat_service.get_chat_id_by_document(document_id)
        if chat_id:
            message_service = PublicMessageService(self._service.db)
            await message_service.send_system_message(chat_id, message)

    # ==========================================
    # 🆕 CREATE & READ
    # ==========================================
    async def create(self, request: CorrectionCreate, created_by: int) -> CorrectionResponse:
        """Создать корректирующее действие. Документ и чат создаются автоматически."""
        result = await self._service.create(request, created_by=created_by)
        await self._send_chat_notification(
            result.document_id,
            f"🛠 Создано корректирующее действие: {result.track_id} — {result.title or 'Без названия'}",
        )
        return result

    async def get_by_id(self, correction_id: int) -> Optional[CorrectionResponse]:
        return await self._service.get_by_id(correction_id)

    async def get_by_document_id(self, doc_id: int) -> Optional[CorrectionResponse]:
        return await self._service.get_by_document_id(doc_id)

    async def get_by_track_id(self, track_id: str) -> Optional[CorrectionResponse]:
        return await self._service.get_by_track_id(track_id)

    async def get_by_problem_registration_id(self, pr_id: int) -> Optional[CorrectionResponse]:
        return await self._service.get_by_problem_registration_id(pr_id)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[CorrectionFilter] = None,
    ) -> CorrectionListResponse:
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return CorrectionListResponse(items=result["items"], total=result["total"])

    # ==========================================
    # ✏️ UPDATE & DELETE
    # ==========================================
    async def update(self, correction_id: int, request: CorrectionUpdate) -> Optional[CorrectionResponse]:
        item = await self.get_by_id(correction_id)
        if item and item.is_locked:
            raise ValueError("Редактирование заблокированного документа невозможно")

        result = await self._service.update(correction_id, request)
        if not result:
            return None

        # Формируем лог изменений для чата
        changes = []
        update_data = request.model_dump(exclude_unset=True)
        if update_data.get("title"): changes.append(f"Название: {update_data['title']}")
        if update_data.get("description"): changes.append("Описание изменено")
        if update_data.get("corrective_action"): changes.append("Выполненные действия изменены")
        if update_data.get("status"): changes.append(f"Статус: {update_data['status']}")
        if update_data.get("planned_date"): changes.append("Плановый срок изменён")
        if update_data.get("completed_date"): changes.append("Фактическая дата выполнения указана")

        if changes:
            await self._send_chat_notification(
                result.document_id,
                f"✏️ Коррекция {result.track_id} обновлена: {'; '.join(changes)}",
            )
        return result

    async def delete(self, correction_id: int) -> bool:
        item = await self.get_by_id(correction_id)
        if item:
            await self._send_chat_notification(
                item.document_id,
                f"🗑️ Корректирующее действие {item.track_id} удалено",
            )
        return await self._service.delete(correction_id)

    # ==========================================
    # 🔒 LOCK / UNLOCK (CONFIRM)
    # ==========================================
    async def confirm(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Подтвердить коррекцию (заблокировать документ)."""
        item = await self.get_by_id(correction_id)
        if not item or item.is_locked:
            return item

        await self._service.doc_service.lock(item.document_id, user_id=user_id)
        await self._send_chat_notification(
            item.document_id,
            f"🔒 Коррекция {item.track_id} подтверждена и заблокирована",
        )
        return await self.get_by_id(correction_id)

    async def unconfirm(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Снять блокировку коррекции."""
        item = await self.get_by_id(correction_id)
        if not item or not item.is_locked:
            return item

        await self._service.doc_service.unlock(item.document_id, user_id=user_id)
        await self._send_chat_notification(
            item.document_id,
            f"🔓 Коррекция {item.track_id} передана на редактирование",
        )
        return await self.get_by_id(correction_id)

    # ==========================================
    # 📦 ARCHIVE / UNARCHIVE
    # ==========================================
    async def archive(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        item = await self.get_by_id(correction_id)
        if not item: return None
        await self._service.archive_document(item.document_id, user_id=user_id)
        await self._send_chat_notification(item.document_id, f"📦 Коррекция {item.track_id} архивирована")
        return await self.get_by_id(correction_id)

    async def unarchive(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        item = await self.get_by_id(correction_id)
        if not item: return None
        await self._service.unarchive_document(item.document_id, user_id=user_id)
        await self._send_chat_notification(item.document_id, f"♻️ Коррекция {item.track_id} восстановлена из архива")
        return await self.get_by_id(correction_id)

    # ==========================================
    # 👤 ASSIGN / UNASSIGN
    # ==========================================
    async def assign_user(self, correction_id: int, user_id_to_assign: int, current_user_id: int) -> Optional[CorrectionResponse]:
        item = await self.get_by_id(correction_id)
        if not item: return None

        await self._service.assign_user_to_document(item.document_id, user_id_to_assign, current_user_id)
        await self._send_chat_notification(
            item.document_id,
            f"👤 Пользователь ID {user_id_to_assign} назначен на коррекцию {item.track_id}",
        )

        # Добавляем в чат
        from app.messages.public_services import PublicChatService
        chat_service = PublicChatService(self._service.db)
        try:
            await chat_service.add_participant_by_document(item.document_id, user_id_to_assign)
        except ValueError:
            pass  # Уже участник

        return await self.get_by_id(correction_id)

    async def assign_self(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        return await self.assign_user(correction_id, user_id, user_id)

    async def unassign(self, correction_id: int, current_user_id: int) -> Optional[CorrectionResponse]:
        item = await self.get_by_id(correction_id)
        if not item or not item.assigned_to:
            return item

        await self._service.doc_service.unassign(item.document_id)
        await self._send_chat_notification(
            item.document_id,
            f"👤 Пользователь снят с коррекции {item.track_id}",
        )
        return await self.get_by_id(correction_id)

    # ==========================================
    # 📋 MY / ASSIGNED LISTS
    # ==========================================
    async def get_my(self, user_id: int, skip: int = 0, limit: int = 20) -> CorrectionListResponse:
        filters = CorrectionFilter(created_by=user_id, sort_by="id", sort_order="desc")
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return CorrectionListResponse(items=result["items"], total=result["total"])

    async def get_assigned(self, user_id: int, skip: int = 0, limit: int = 20) -> CorrectionListResponse:
        filters = CorrectionFilter(assigned_to=user_id, sort_by="id", sort_order="desc")
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return CorrectionListResponse(items=result["items"], total=result["total"])

    # ==========================================
    # 🔄 STATUS WORKFLOW (ЗАГЛУШКИ ИЗ ОБРАЗЦА → РЕАЛИЗАЦИЯ)
    # ==========================================
    async def change_status(self, correction_id: int, new_status: CorrectionStatus, user_id: int) -> Optional[CorrectionResponse]:
        """Автоматически проставляет даты и исполнителей при смене статуса."""
        item = await self.get_by_id(correction_id)
        if not item or item.is_locked:
            raise ValueError("Изменение статуса заблокированного документа невозможно")

        # Готовим payload для update
        update_data = {
            "status": new_status,
            "completed_by": user_id,
            "completed_date": None,
        }

        # Бизнес-правила статусов
        if new_status == CorrectionStatus.COMPLETED:
            update_data["completed_date"] = datetime.now(timezone.utc)
        elif new_status == CorrectionStatus.REJECTED:
            update_data["completed_date"] = None  # Сброс при отказе

        from pydantic import TypeAdapter
        # Преобразуем dict в схему Update для валидации
        adapter = TypeAdapter(CorrectionUpdate)
        validated_update = adapter.validate_python(update_data)
        
        result = await self._service.update(correction_id, validated_update)
        
        await self._send_chat_notification(
            result.document_id,
            f"🔄 Статус коррекции {item.track_id} изменён на: {new_status.value}",
        )
        return result

    async def close(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Завершить и верифицировать коррекцию."""
        return await self.change_status(correction_id, CorrectionStatus.VERIFIED, user_id)