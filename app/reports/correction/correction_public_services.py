# app/reports/correction/correction_public_services.py
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select  # 🔹 Добавлено
from datetime import datetime, timezone
from fastapi import HTTPException, status  # 🔹 Добавлено

from app.reports.correction.correction_service import CorrectionService
from app.reports.documents.document_public_service import PublicDocumentService
from app.reports.correction.schemas.correction import (
    CorrectionCreate,
    CorrectionUpdate,
    CorrectionResponse,
    CorrectionListResponse,
    CorrectionFilter,
)
from app.reports.correction.models import CorrectionStatus
from app.auth.models import User  # 🔹 Добавлено


class PublicCorrectionService:
    """
    Публичный фасад для работы с корректирующими действиями.
    Координирует статусы, уведомления, блокировки документа и аудит.
    """

    def __init__(self, db: AsyncSession):
        doc_service = PublicDocumentService(db)
        self._service = CorrectionService(db, doc_service)
        self.db = db

    # ------------------------------------------------------------------
    # 🔔 Нотификации
    # ------------------------------------------------------------------
    async def _send_chat_notification(self, document_id: int, message: str):
        """Отправить уведомление в чат, привязанный к документу."""
        from app.messages.public_services import PublicChatService, PublicMessageService
        
        chat_service = PublicChatService(self.db)
        chat_id = await chat_service.get_chat_id_by_document(document_id)
        if chat_id:
            message_service = PublicMessageService(self.db)
            await message_service.send_system_message(chat_id, message)

    # ------------------------------------------------------------------
    # 🔹 Вспомогательный метод: загрузка пользователя
    # ------------------------------------------------------------------
    async def _get_user_or_404(self, user_id: int) -> User:
        """Загружает объект User или выбрасывает 404."""
        res = await self.db.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    # ------------------------------------------------------------------
    # 🔹 CRUD
    # ------------------------------------------------------------------
    async def create(self, request: CorrectionCreate, created_by: int) -> CorrectionResponse:
        """Создать корректирующее действие. Документ должен существовать."""
        current_user = await self._get_user_or_404(created_by)
        result = await self._service.create(request, current_user=current_user)
        await self._send_chat_notification(
            result.document_id,
            f"🛠️ Создано корректирующее действие: {result.title}",
        )
        return result

    async def get_by_id(self, correction_id: int) -> Optional[CorrectionResponse]:
        return await self._service.get_by_id(correction_id)

    async def get_by_document_id(self, doc_id: int) -> List[CorrectionResponse]:
        """Все активные коррекции по документу."""
        return await self._service.get_by_document_id(doc_id)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[CorrectionFilter] = None,
    ) -> CorrectionListResponse:
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return CorrectionListResponse(items=result["items"], total=result["total"])

    async def update(self, correction_id: int, request: CorrectionUpdate, current_user_id: int) -> Optional[CorrectionResponse]:
        """Частичное обновление. Блокирует редактирование, если документ залочен."""
        item = await self.get_by_id(correction_id)
        if not item:
            return None
        if item.is_locked:
            raise ValueError("Редактирование заблокированной коррекции невозможно")

        current_user = await self._get_user_or_404(current_user_id)
        result = await self._service.update(correction_id, request, current_user=current_user)
        if not result:
            return None

        # Формируем лог изменений для чата
        changes = []
        update_data = request.model_dump(exclude_unset=True)
        if update_data.get("title"):
            changes.append(f"Название: {update_data['title']}")
        if update_data.get("corrective_action"):
            changes.append("Действия изменены")
        if update_data.get("planned_date"):
            changes.append("Плановый срок изменён")

        if changes:
            await self._send_chat_notification(
                result.document_id,
                f"✏️ Коррекция {result.track_id} обновлена: {'; '.join(changes)}",
            )
        return result

    async def delete(self, correction_id: int) -> bool:
        """Soft-delete коррекции."""
        item = await self.get_by_id(correction_id)
        if item:
            await self._send_chat_notification(
                item.document_id,
                f"🗑️ Корректирующее действие {item.track_id} удалено",
            )
        return await self._service.delete(correction_id)

    # ------------------------------------------------------------------
    # 🔄 Статусные переходы (публичные методы-обёртки)
    # ------------------------------------------------------------------
    async def start_execution(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """PLANNED → IN_PROGRESS"""
        item = await self.get_by_id(correction_id)
        if not item or item.is_locked:
            raise ValueError("Нельзя начать выполнение: коррекция не найдена или заблокирована")
        return await self._change_status(correction_id, CorrectionStatus.IN_PROGRESS, user_id)

    async def complete_execution(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """IN_PROGRESS → COMPLETED (авто-фиксация даты и исполнителя)"""
        item = await self.get_by_id(correction_id)
        if not item or item.is_locked:
            raise ValueError("Нельзя завершить: коррекция не найдена или заблокирована")
        return await self._change_status(correction_id, CorrectionStatus.COMPLETED, user_id)

    async def verify(self, correction_id: int, verifier_id: int) -> Optional[CorrectionResponse]:
        """COMPLETED → VERIFIED"""
        item = await self.get_by_id(correction_id)
        if not item:
            raise ValueError("Коррекция не найдена")
        return await self._change_status(correction_id, CorrectionStatus.VERIFIED, verifier_id)

    async def reject(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Сброс статуса: IN_PROGRESS/COMPLETED → REJECTED или PLANNED"""
        item = await self.get_by_id(correction_id)
        if not item:
            raise ValueError("Коррекция не найдена")
        return await self._change_status(correction_id, CorrectionStatus.REJECTED, user_id)

    async def _change_status(self, correction_id: int, target_status: CorrectionStatus, user_id: int) -> Optional[CorrectionResponse]:
        """Внутренний метод смены статуса с валидацией и нотификацией."""
        current_user = await self._get_user_or_404(user_id)
        update_req = CorrectionUpdate(status=target_status)
        result = await self._service.update(correction_id, update_req, current_user=current_user)
        if result:
            await self._send_chat_notification(
                result.document_id,
                f"📊 Статус коррекции {result.track_id} изменён на: {result.status.upper()}",
            )
        return result

    # ------------------------------------------------------------------
    # 🔒 Блокировка / Подтверждение / Архив
    # ------------------------------------------------------------------
    async def confirm(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Заблокировать коррекцию и родительский документ."""
        item = await self.get_by_id(correction_id)
        if not item:
            return None
        if item.is_locked:
            return item

        current_user = await self._get_user_or_404(user_id)
        await self._service.doc_service.lock(item.document_id, user_id=current_user.id)
        await self._send_chat_notification(
            item.document_id,
            f"🔒 Коррекция {item.track_id} подтверждена и заблокирована",
        )
        return await self.get_by_id(correction_id)

    async def unconfirm(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Разблокировать для редактирования."""
        item = await self.get_by_id(correction_id)
        if not item or not item.is_locked:
            return item

        current_user = await self._get_user_or_404(user_id)
        await self._service.doc_service.unlock(item.document_id, user_id=current_user.id)
        await self._send_chat_notification(
            item.document_id,
            f"🔓 Коррекция {item.track_id} разблокирована для редактирования",
        )
        return await self.get_by_id(correction_id)

    async def archive(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Архивировать вместе с документом."""
        item = await self.get_by_id(correction_id)
        if not item:
            return None
        current_user = await self._get_user_or_404(user_id)
        await self._service.doc_service.archive(item.document_id, user_id=current_user.id)
        await self._send_chat_notification(item.document_id, f"📦 Коррекция {item.track_id} архивирована")
        return await self.get_by_id(correction_id)

    async def unarchive(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Восстановить из архива."""
        item = await self.get_by_id(correction_id)
        if not item:
            return None
        current_user = await self._get_user_or_404(user_id)
        await self._service.doc_service.unarchive(item.document_id, user_id=current_user.id)
        await self._send_chat_notification(item.document_id, f"📦 Коррекция {item.track_id} восстановлена из архива")
        return await self.get_by_id(correction_id)

    # ------------------------------------------------------------------
    # 👤 Назначения (делегирование на уровень документа)
    # ------------------------------------------------------------------
    async def assign_user(self, correction_id: int, user_id_to_assign: int, current_user_id: int) -> Optional[CorrectionResponse]:
        """Назначить исполнителя на документ/коррекцию."""
        item = await self.get_by_id(correction_id)
        if not item:
            return None

        current_user = await self._get_user_or_404(current_user_id)
        await self._service.doc_service.assign_to_user(item.document_id, user_id_to_assign, current_user_id=current_user.id)
        await self._send_chat_notification(
            item.document_id,
            f"👤 Пользователь ID {user_id_to_assign} назначен на коррекцию {item.track_id}",
        )

        # Добавляем в чат документа
        from app.messages.public_services import PublicChatService
        chat_service = PublicChatService(self.db)
        try:
            await chat_service.add_participant_by_document(item.document_id, user_id_to_assign)
        except ValueError:
            pass

        return await self.get_by_id(correction_id)

    async def assign_self(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Назначить себя."""
        return await self.assign_user(correction_id, user_id, user_id)

    async def unassign(self, correction_id: int, current_user_id: int) -> Optional[CorrectionResponse]:
        """Снять назначение."""
        item = await self.get_by_id(correction_id)
        if not item or not item.assigned_to:
            return item

        current_user = await self._get_user_or_404(current_user_id)
        await self._service.doc_service.unassign(item.document_id, current_user_id=current_user.id)
        await self._send_chat_notification(
            item.document_id,
            f"👤 Исполнитель снят с коррекции {item.track_id}",
        )
        return await self.get_by_id(correction_id)

    # ------------------------------------------------------------------
    # 📋 Персональные списки
    # ------------------------------------------------------------------
    async def get_my(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> CorrectionListResponse:
        """Коррекции, созданные пользователем."""
        filters = CorrectionFilter(created_by=user_id, sort_by="created_at", sort_order="desc")
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return CorrectionListResponse(items=result["items"], total=result["total"])

    async def get_assigned(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> CorrectionListResponse:
        """Коррекции, назначенные на пользователя (через документ)."""
        # В фильтрах используем assigned_to документа
        filters = CorrectionFilter(doc_assigned_to=user_id, sort_by="created_at", sort_order="desc")
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return CorrectionListResponse(items=result["items"], total=result["total"])