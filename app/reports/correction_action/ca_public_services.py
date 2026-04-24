from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.reports.correction_action.ca_service import CorrectionActionService
from app.reports.correction_action.ca_models import CorrectionActionStatus
from app.reports.correction_action.ca_schemas import (
    CorrectionActionCreate,
    CorrectionActionUpdate,
    CorrectionActionResponse,
    CorrectionActionFilter,
    CorrectionActionListResponse,
)

from app.reports.documents.document_public_service import PublicDocumentService


class PublicCorrectionActionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._doc_service = PublicDocumentService(db)
        self._service = CorrectionActionService(db, self._doc_service)


    # =========================================================
    # 🔔 NOTIFICATIONS
    # =========================================================
    async def _send_chat_notification(self, document_id: int, message: str):
        from app.messages.public_services import PublicChatService, PublicMessageService

        chat_service = PublicChatService(self.db)
        chat_id = await chat_service.get_chat_id_by_document(document_id)

        if chat_id:
            message_service = PublicMessageService(self.db)
            await message_service.send_system_message(chat_id, message)

    async def _check_document_lock(self, document_id: int):
        doc_status = await self._doc_service.get_status_and_lock(document_id)
        if doc_status.get("is_locked"):
            raise ValueError("Документ заблокирован")

    # =========================================================
    # CREATE
    # =========================================================
    async def create(
        self, request: CorrectionActionCreate, created_by: int
    ) -> CorrectionActionResponse:


        result = await self._service.create(request, created_by)

        await self._send_chat_notification(
            result.document_id,
            f"🔧 Создано действие #{result.id}",
        )

        return result

    # =========================================================
    # READ
    # =========================================================
    async def get_by_id(self, action_id: int):
        return await self._service.get_by_id(action_id)

    async def get_all(
        self, filters: Optional[CorrectionActionFilter] = None
    ) -> CorrectionActionListResponse:
        return await self._service.get_all(filters)

    async def get_by_correction_id(
        self, correction_id: int, filters: Optional[CorrectionActionFilter] = None
    ) -> CorrectionActionListResponse:

        if not filters:
            filters = CorrectionActionFilter()

        filters.correction_id = correction_id
        return await self._service.get_all(filters)

    async def get_assigned(
        self, user_id: int, filters: Optional[CorrectionActionFilter] = None
    ) -> CorrectionActionListResponse:

        if not filters:
            filters = CorrectionActionFilter()

        filters.assigned_user_id = user_id
        return await self._service.get_all(filters)

    # =========================================================
    # UPDATE
    # =========================================================
    async def update(
        self,
        action_id: int,
        request: CorrectionActionUpdate,
    ) -> Optional[CorrectionActionResponse]:

        item = await self._service.get_by_id(action_id)
        if not item:
            return None

        await self._check_document_lock(item.document_id)

        result = await self._service.update(action_id, request)
        if not result:
            return None

        # 📢 уведомление только при значимых изменениях
        if request.status:
            await self._send_chat_notification(
                item.document_id,
                f"📊 Действие #{result.id}: статус → {request.status}",
            )

        if request.assigned_user_id is not None:
            await self._send_chat_notification(
                item.document_id,
                f"👤 Назначен исполнитель для действия #{result.id}",
            )

        return result

    # =========================================================
    # STATUS SHORTCUTS
    # =========================================================
    async def start_action(self, action_id: int):
        return await self.update(
            action_id,
            CorrectionActionUpdate(status=CorrectionActionStatus.IN_PROGRESS),
        )

    async def complete_action(self, action_id: int, comment: Optional[str] = None):
        return await self.update(
            action_id,
            CorrectionActionUpdate(
                status=CorrectionActionStatus.COMPLETED,
                comment=comment,
            ),
        )

    async def skip_action(self, action_id: int, comment: Optional[str] = None):
        return await self.update(
            action_id,
            CorrectionActionUpdate(
                status=CorrectionActionStatus.SKIPPED,
                comment=comment,
            ),
        )

    # =========================================================
    # ASSIGNMENT
    # =========================================================
    async def assign_user(self, action_id: int, user_id: int):
        return await self.update(
            action_id,
            CorrectionActionUpdate(assigned_user_id=user_id),
        )

    async def unassign(self, action_id: int):
        return await self.update(
            action_id,
            CorrectionActionUpdate(assigned_user_id=None),
        )

    # =========================================================
    # DELETE
    # =========================================================
    async def delete(self, action_id: int) -> bool:
        item = await self._service.get_by_id(action_id)

        if item:
            await self._check_document_lock(item.document_id)

            await self._send_chat_notification(
                item.document_id,
                f"🗑️ Удалено действие #{action_id}",
            )

        return await self._service.delete(action_id)

    # =========================================================
    # BULK
    # =========================================================
    async def close_correction_actions(self, correction_id: int) -> int:
        filters = CorrectionActionFilter(correction_id=correction_id, limit=1000)

        actions = await self._service.get_all(filters)

        count = 0
        for action in actions.items:
            if action.status not in (
                CorrectionActionStatus.COMPLETED,
                CorrectionActionStatus.SKIPPED,
            ):
                await self.skip_action(action.id)
                count += 1

        return count