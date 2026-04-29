# app/reports/correction/correction_public_service.py
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from loguru import logger

from app.reports.correction.correction_service import CorrectionService
from app.reports.documents.document_public_service import PublicDocumentService
from app.reports.correction.correction_schemas import (
    CorrectionCreate,
    CorrectionUpdate,
    CorrectionResponse,
    CorrectionListResponse,
    CorrectionFilter,
    CorrectionStatus,
)


class PublicCorrectionService:
    """Публичный слой корректирующих действий."""

    def __init__(self, db: AsyncSession):
        self.db = db  # ✅ Сохраняем ссылку на db для внутренних сервисов
        doc_service = PublicDocumentService(db)
        self._service = CorrectionService(db, doc_service)
        logger.debug("PublicCorrectionService initialized")

    async def _send_chat_notification(self, document_id: int, message: str):
        """Отправить системное уведомление в чат документа."""
        try:
            from app.messages.public_services import PublicChatService, PublicMessageService
            chat_service = PublicChatService(self.db)
            chat_id = await chat_service.get_chat_id_by_document(document_id)
            if chat_id:
                message_service = PublicMessageService(self.db)
                await message_service.send_system_message(chat_id, message)
                logger.debug("Chat notification sent", document_id=document_id, message=message[:100])
        except Exception as e:
            logger.warning("Failed to send chat notification", document_id=document_id, error=str(e))

    # ==========================================
    # 🆕 CREATE & READ
    # ==========================================
    async def create(self, request: CorrectionCreate, created_by: int) -> CorrectionResponse:
        """Создать корректирующее действие. Документ и чат создаются автоматически."""
        logger.info("Creating correction via public service", created_by=created_by, title=request.title)
        result = await self._service.create(request, created_by=created_by)
        await self._send_chat_notification(
            result.document_id,
            f"🛠 Создано корректирующее действие: {result.track_id} — {result.title or 'Без названия'}",
        )
        logger.info("Correction created successfully", correction_id=result.id, track_id=result.track_id)
        return result

    async def get_by_id(self, correction_id: int) -> Optional[CorrectionResponse]:
        logger.debug("Fetching correction by ID via public service", correction_id=correction_id)
        return await self._service.get_by_id(correction_id)

    async def get_by_document_id(self, doc_id: int) -> Optional[CorrectionResponse]:
        logger.debug("Fetching correction by document ID", doc_id=doc_id)
        return await self._service.get_by_document_id(doc_id)

    async def get_by_track_id(self, track_id: str) -> Optional[CorrectionResponse]:
        logger.debug("Fetching correction by track_id", track_id=track_id)
        return await self._service.get_by_track_id(track_id)

    async def get_by_target_document_id(self, pr_id: int) -> Optional[CorrectionResponse]:
        logger.debug("Fetching correction by target_document_id", pr_id=pr_id)
        return await self._service.get_by_target_document_id(pr_id)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[CorrectionFilter] = None,
    ) -> CorrectionListResponse:
        logger.debug("Listing corrections via public service", skip=skip, limit=limit)
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return CorrectionListResponse(items=result["items"], total=result["total"])

    # ==========================================
    # ✏️ UPDATE & DELETE
    # ==========================================
    async def update(self, correction_id: int, request: CorrectionUpdate) -> Optional[CorrectionResponse]:
        logger.info("Updating correction via public service", correction_id=correction_id)
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Correction not found for update", correction_id=correction_id)
            return None
        if item.is_locked:
            logger.warning("Cannot update locked correction", correction_id=correction_id)
            raise ValueError("Редактирование заблокированного документа невозможно")

        result = await self._service.update(correction_id, request)
        if not result:
            logger.warning("Correction update returned None", correction_id=correction_id)
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
        logger.info("Correction updated successfully", correction_id=correction_id)
        return result

    async def delete(self, correction_id: int) -> bool:
        logger.info("Deleting correction via public service", correction_id=correction_id)
        item = await self.get_by_id(correction_id)
        if item:
            await self._send_chat_notification(
                item.document_id,
                f"🗑️ Корректирующее действие {item.track_id} удалено",
            )
        result = await self._service.delete(correction_id)
        logger.info("Correction deleted", correction_id=correction_id, success=result)
        return result

    # ==========================================
    # 🔒 LOCK / UNLOCK (CONFIRM)
    # ==========================================
    async def confirm(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Подтвердить коррекцию (заблокировать документ)."""
        logger.info("Confirming (locking) correction", correction_id=correction_id, user_id=user_id)
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Correction not found for confirm", correction_id=correction_id)
            return None
        if item.is_locked:
            logger.debug("Correction already locked", correction_id=correction_id)
            return item

        await self._service.doc_service.lock(item.document_id, user_id=user_id)
        await self._send_chat_notification(
            item.document_id,
            f"🔒 Коррекция {item.track_id} подтверждена и заблокирована",
        )
        logger.info("Correction confirmed", correction_id=correction_id)
        return await self.get_by_id(correction_id)

    async def unconfirm(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Снять блокировку коррекции."""
        logger.info("Unconfirming (unlocking) correction", correction_id=correction_id, user_id=user_id)
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Correction not found for unconfirm", correction_id=correction_id)
            return None
        if not item.is_locked:
            logger.debug("Correction already unlocked", correction_id=correction_id)
            return item

        await self._service.doc_service.unlock(item.document_id, user_id=user_id)
        await self._send_chat_notification(
            item.document_id,
            f"🔓 Коррекция {item.track_id} передана на редактирование",
        )
        logger.info("Correction unconfirmed", correction_id=correction_id)
        return await self.get_by_id(correction_id)

    # ==========================================
    # 📦 ARCHIVE / UNARCHIVE
    # ==========================================
    async def archive(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        logger.info("Archiving correction", correction_id=correction_id, user_id=user_id)
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Correction not found for archive", correction_id=correction_id)
            return None
        await self._service.archive_document(item.document_id, user_id=user_id)
        await self._send_chat_notification(item.document_id, f"📦 Коррекция {item.track_id} архивирована")
        logger.info("Correction archived", correction_id=correction_id)
        return await self.get_by_id(correction_id)

    async def unarchive(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        logger.info("Unarchiving correction", correction_id=correction_id, user_id=user_id)
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Correction not found for unarchive", correction_id=correction_id)
            return None
        await self._service.unarchive_document(item.document_id, user_id=user_id)
        await self._send_chat_notification(item.document_id, f"♻️ Коррекция {item.track_id} восстановлена из архива")
        logger.info("Correction unarchived", correction_id=correction_id)
        return await self.get_by_id(correction_id)

    # ==========================================
    # 👤 ASSIGN / UNASSIGN
    # ==========================================
    async def assign_user(self, correction_id: int, user_id_to_assign: int, current_user_id: int) -> Optional[CorrectionResponse]:
        logger.info("Assigning user to correction", correction_id=correction_id, assignee=user_id_to_assign, by=current_user_id)
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Correction not found for assign", correction_id=correction_id)
            return None

        await self._service.assign_user_to_document(item.document_id, user_id_to_assign, current_user_id)
        await self._send_chat_notification(
            item.document_id,
            f"👤 Пользователь ID {user_id_to_assign} назначен на коррекцию {item.track_id}",
        )

        # Добавляем в чат
        from app.messages.public_services import PublicChatService
        chat_service = PublicChatService(self.db)
        try:
            await chat_service.add_participant_by_document(item.document_id, user_id_to_assign)
            logger.debug("User added to chat", user_id=user_id_to_assign, document_id=item.document_id)
        except ValueError:
            logger.debug("User already in chat", user_id=user_id_to_assign, document_id=item.document_id)

        logger.info("User assigned to correction", correction_id=correction_id, assignee=user_id_to_assign)
        return await self.get_by_id(correction_id)

    async def assign_self(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        logger.info("User assigning self to correction", correction_id=correction_id, user_id=user_id)
        return await self.assign_user(correction_id, user_id, user_id)

    async def unassign(self, correction_id: int, current_user_id: int) -> Optional[CorrectionResponse]:
        logger.info("Unassigning user from correction", correction_id=correction_id, by=current_user_id)
        item = await self.get_by_id(correction_id)
        if not item or not item.assigned_to:
            logger.debug("No assignment to remove", correction_id=correction_id)
            return item

        await self._service.doc_service.unassign(item.document_id)
        await self._send_chat_notification(
            item.document_id,
            f"👤 Пользователь снят с коррекции {item.track_id}",
        )
        logger.info("User unassigned from correction", correction_id=correction_id)
        return await self.get_by_id(correction_id)

    # ==========================================
    # 📋 MY / ASSIGNED LISTS
    # ==========================================
    async def get_my(self, user_id: int, skip: int = 0, limit: int = 20) -> CorrectionListResponse:
        logger.debug("Fetching user's corrections", user_id=user_id, skip=skip, limit=limit)
        filters = CorrectionFilter(created_by=user_id, sort_by="id", sort_order="desc")
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return CorrectionListResponse(items=result["items"], total=result["total"])

    async def get_assigned(self, user_id: int, skip: int = 0, limit: int = 20) -> CorrectionListResponse:
        logger.debug("Fetching corrections assigned to user", user_id=user_id, skip=skip, limit=limit)
        filters = CorrectionFilter(assigned_to=user_id, sort_by="id", sort_order="desc")
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return CorrectionListResponse(items=result["items"], total=result["total"])

    # ==========================================
    # 🔄 STATUS WORKFLOW
    # ==========================================
    async def change_status(self, correction_id: int, new_status: CorrectionStatus, user_id: int) -> Optional[CorrectionResponse]:
        """Автоматически проставляет даты и исполнителей при смене статуса."""
        logger.info("Changing correction status", correction_id=correction_id, new_status=new_status.value, user_id=user_id)
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Correction not found for status change", correction_id=correction_id)
            return None
        if item.is_locked:
            logger.warning("Cannot change status of locked correction", correction_id=correction_id)
            raise ValueError("Изменение статуса заблокированного документа невозможно")

        update_data = {
            "status": new_status,
            "completed_by": user_id if new_status == CorrectionStatus.COMPLETED else None,
            "completed_date": None,
        }

        if new_status == CorrectionStatus.COMPLETED:
            update_data["completed_date"] = datetime.now(timezone.utc)
            logger.debug("Setting completed_date for COMPLETED status")
        elif new_status == CorrectionStatus.REJECTED:
            update_data["completed_date"] = None
            logger.debug("Clearing completed_date for REJECTED status")

        from pydantic import TypeAdapter
        adapter = TypeAdapter(CorrectionUpdate)
        validated_update = adapter.validate_python(update_data)
        
        result = await self._service.update(correction_id, validated_update)
        if result:
            await self._send_chat_notification(
                result.document_id,
                f"🔄 Статус коррекции {item.track_id} изменён на: {new_status.value}",
            )
            logger.info("Correction status changed successfully", correction_id=correction_id, new_status=new_status.value)
        return result

    async def close(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Завершить и верифицировать коррекцию."""
        logger.info("Closing (verifying) correction", correction_id=correction_id, user_id=user_id)
        result = await self.change_status(correction_id, CorrectionStatus.VERIFIED, user_id)
        if result:
            logger.info("Correction closed successfully", correction_id=correction_id)
        return result

    

    async def complete(self, correction_id: int, user_id: int, completed_date: Optional[datetime] = None) -> Optional[CorrectionResponse]:
        """Отметить коррекцию как выполненную."""
        logger.info("Marking correction as completed", correction_id=correction_id, user_id=user_id)
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Correction not found for complete", correction_id=correction_id)
            return None
        if item.is_locked:
            logger.warning("Cannot complete locked correction", correction_id=correction_id)
            raise ValueError("Действие с заблокированным документом невозможно")

        from pydantic import TypeAdapter
        adapter = TypeAdapter(CorrectionUpdate)
        validated_update = adapter.validate_python({
            "status": CorrectionStatus.COMPLETED,
            "completed_by": user_id,
            "completed_date": completed_date or datetime.now(timezone.utc),
        })
        
        result = await self._service.update(correction_id, validated_update)
        if result:
            await self._send_chat_notification(
                result.document_id,
                f"✅ Коррекция {result.track_id} отмечена как выполненная",
            )
            logger.info("Correction marked as completed", correction_id=correction_id)
        return result

    async def verify(self, correction_id: int, user_id: int) -> Optional[CorrectionResponse]:
        """Верифицировать выполненную коррекцию."""
        logger.info("Verifying correction", correction_id=correction_id, user_id=user_id)
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Correction not found for verify", correction_id=correction_id)
            return None
        if item.status != CorrectionStatus.COMPLETED.value:
            logger.warning("Cannot verify non-completed correction", correction_id=correction_id, current_status=item.status)
            raise ValueError("Верифицировать можно только завершённую коррекцию")
        if item.is_locked:
            logger.warning("Cannot verify locked correction", correction_id=correction_id)
            raise ValueError("Действие с заблокированным документом невозможно")

        from pydantic import TypeAdapter
        adapter = TypeAdapter(CorrectionUpdate)
        validated_update = adapter.validate_python({
            "status": CorrectionStatus.VERIFIED,
            "verified_by": user_id,
        })
        
        result = await self._service.update(correction_id, validated_update)
        if result:
            await self._send_chat_notification(
                result.document_id,
                f"🔍 Коррекция {result.track_id} верифицирована",
            )
            logger.info("Correction verified", correction_id=correction_id)
        return result

    async def reject(self, correction_id: int, user_id: int, comment: Optional[str] = None) -> Optional[CorrectionResponse]:
        """Отклонить коррекцию с комментарием."""
        logger.info("Rejecting correction", correction_id=correction_id, user_id=user_id)
        item = await self.get_by_id(correction_id)
        if not item:
            logger.warning("Correction not found for reject", correction_id=correction_id)
            return None
        if item.is_locked:
            logger.warning("Cannot reject locked correction", correction_id=correction_id)
            raise ValueError("Действие с заблокированным документом невозможно")

        from pydantic import TypeAdapter
        adapter = TypeAdapter(CorrectionUpdate)
        validated_update = adapter.validate_python({
            "status": CorrectionStatus.REJECTED,
            "comment": comment,
        })
        
        result = await self._service.update(correction_id, validated_update)
        if result:
            await self._send_chat_notification(
                result.document_id,
                f"❌ Коррекция {result.track_id} отклонена" + (f": {comment}" if comment else ""),
            )
            logger.info("Correction rejected", correction_id=correction_id, comment=comment)
        return result