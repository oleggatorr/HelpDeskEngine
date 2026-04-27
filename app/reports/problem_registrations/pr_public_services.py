# app/reports/problem_registrations/pr_public_services.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.reports.problem_registrations.pr_service import ProblemRegistrationService
from app.reports.documents.document_public_service import PublicDocumentService
from app.reports.problem_registrations.pr_schemas import (
    ProblemRegistrationCreate,
    ProblemRegistrationUpdate,
    ProblemRegistrationResponse,
    ProblemRegistrationListResponse,
    ProblemRegistration_DetaleUpdate,
)


class PublicProblemRegistrationService:
    """Публичный слой регистраций проблем."""

    def __init__(self, db: AsyncSession):
        doc_service = PublicDocumentService(db)
        self._service = ProblemRegistrationService(db, doc_service)
        logger.debug("PublicProblemRegistrationService initialized")

    async def _send_chat_notification(self, document_id: int, message: str):
        """Отправить уведомление в чат, привязанный к документу."""
        logger.debug("Preparing chat notification", doc_id=document_id)
        try:
            from app.messages.public_services import PublicChatService, PublicMessageService
            chat_service = PublicChatService(self._service.db)
            chat_id = await chat_service.get_chat_id_by_document(document_id)
            if chat_id:
                message_service = PublicMessageService(self._service.db)
                await message_service.send_system_message(chat_id, message)
                logger.debug("Chat notification sent successfully", chat_id=chat_id)
            else:
                logger.debug("No chat found for document, skipping notification", doc_id=document_id)
        except Exception as e:
            logger.warning("Failed to send chat notification (non-critical)", doc_id=document_id, error=str(e))

    async def create(self, request: ProblemRegistrationCreate, created_by: int) -> ProblemRegistrationResponse:
        """Создать регистрацию проблемы. Документ создаётся автоматически."""
        logger.info("Creating problem registration", created_by=created_by, subject=request.subject)
        result = await self._service.create(request, created_by=created_by)
        
        await self._send_chat_notification(
            result.document_id,
            f"📄 Создана новая регистрация проблемы: {result.track_id} — {result.subject or 'Без темы'}",
        )
        logger.info("Problem registration created successfully", reg_id=result.id, track_id=result.track_id)
        return result

    async def get_by_id(self, registration_id: int) -> Optional[ProblemRegistrationResponse]:
        logger.debug("Fetching registration by ID", reg_id=registration_id)
        return await self._service.get_by_id(registration_id)

    async def get_by_document_id(self, doc_id: int) -> Optional[ProblemRegistrationResponse]:
        logger.debug("Fetching registration by document ID", doc_id=doc_id)
        return await self._service.get_by_document_id(doc_id)

    async def get_by_track_id(self, track_id: str) -> Optional[ProblemRegistrationResponse]:
        """Получить регистрацию проблемы по трек-номеру документа."""
        logger.debug("Fetching registration by track_id", track_id=track_id)
        return await self._service.get_by_track_id(track_id)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters=None,
    ) -> ProblemRegistrationListResponse:
        logger.debug("Listing registrations", skip=skip, limit=limit, has_filters=filters is not None)
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        logger.info("Registration list retrieved", total=result["total"], returned=len(result["items"]))
        return ProblemRegistrationListResponse(items=result["items"], total=result["total"])

    async def update(self, registration_id: int, request: ProblemRegistrationUpdate) -> Optional[ProblemRegistrationResponse]:
        """Обновить регистрацию проблемы."""
        logger.info("Updating registration", reg_id=registration_id)
        item = await self.get_by_id(registration_id)
        if item and item.is_locked:
            logger.warning("Update blocked: registration is locked", reg_id=registration_id)
            raise ValueError("Редактирование заблокированного документа невозможно")

        result = await self._service.update(registration_id, request)
        if not result:
            logger.warning("Registration not found during update", reg_id=registration_id)
            return None

        changes = []
        update_data = request.model_dump(exclude_unset=True)
        if update_data.get("subject"):
            changes.append(f"Тема: {update_data['subject']}")
        if update_data.get("description"):
            changes.append("Описание изменено")
        if update_data.get("nomenclature"):
            changes.append(f"Номенклатура: {update_data['nomenclature']}")
        if update_data.get("detected_at"):
            changes.append("Дата обнаружения изменена")
        if update_data.get("location_id"):
            changes.append("Локация изменена")

        if changes:
            await self._send_chat_notification(
                result.document_id,
                f"✏️ Регистрация проблемы {result.track_id} обновлена: {'; '.join(changes)}",
            )
            logger.debug("Change notification sent", reg_id=registration_id, changes=changes)
            
        logger.info("Registration updated successfully", reg_id=registration_id)
        return result

    async def confirm(self, registration_id: int, user_id: int) -> Optional["ProblemRegistrationResponse"]:
        """Публичный метод блокировки регистрации."""
        logger.info("Confirming (locking) registration", reg_id=registration_id, user_id=user_id)
        return await self._service.lock(registration_id, user_id)

    async def unconfirm(self, registration_id: int, user_id: int) -> Optional["ProblemRegistrationResponse"]:
        """Публичный метод разблокировки регистрации."""
        logger.info("Unconfirming (unlocking) registration", reg_id=registration_id, user_id=user_id)
        return await self._service.unlock(registration_id, user_id)

    async def delete(self, registration_id: int) -> bool:
        """Удалить регистрацию проблемы."""
        logger.info("Deleting registration", reg_id=registration_id)
        item = await self.get_by_id(registration_id)
        if item:
            await self._send_chat_notification(
                item.document_id,
                f"🗑️ Регистрация проблемы {item.track_id} удалена",
            )
        result = await self._service.delete(registration_id)
        logger.info("Registration deleted", reg_id=registration_id, success=result)
        return result

    async def get_my(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> ProblemRegistrationListResponse:
        """Получить список регистраций, созданных пользователем."""
        from app.reports.problem_registrations.pr_schemas import ProblemRegistrationFilter
        logger.debug("Fetching user's registrations", user_id=user_id, skip=skip, limit=limit)
        filters = ProblemRegistrationFilter(
            created_by=user_id,
            sort_by="id",
            sort_order="desc",
        )
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return ProblemRegistrationListResponse(items=result["items"], total=result["total"])

    async def get_assigned(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> ProblemRegistrationListResponse:
        """Получить список регистраций, назначенных на пользователя."""
        from app.reports.problem_registrations.pr_schemas import ProblemRegistrationFilter
        logger.debug("Fetching assigned registrations", user_id=user_id, skip=skip, limit=limit)
        filters = ProblemRegistrationFilter(
            assigned_to=user_id,
            sort_by="id",
            sort_order="desc",
        )
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return ProblemRegistrationListResponse(items=result["items"], total=result["total"])

    async def archive(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Архивировать регистрацию проблемы."""
        logger.info("Archiving registration", reg_id=registration_id, user_id=user_id)
        item = await self.get_by_id(registration_id)
        if not item:
            logger.warning("Registration not found for archive", reg_id=registration_id)
            return None
        await self._service.archive_document(item.document_id, user_id=user_id)
        await self._send_chat_notification(
            item.document_id,
            f"📦 Регистрация проблемы {item.track_id} архивирована",
        )
        logger.info("Registration archived successfully", reg_id=registration_id)
        return await self.get_by_id(registration_id)

    async def unarchive(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Восстановить регистрацию проблемы из архива."""
        logger.info("Unarchiving registration", reg_id=registration_id, user_id=user_id)
        item = await self.get_by_id(registration_id)
        if not item:
            logger.warning("Registration not found for unarchive", reg_id=registration_id)
            return None
        await self._service.unarchive_document(item.document_id, user_id=user_id)
        await self._send_chat_notification(
            item.document_id,
            f"📦 Регистрация проблемы {item.track_id} восстановлена из архива",
        )
        logger.info("Registration unarchived successfully", reg_id=registration_id)
        return await self.get_by_id(registration_id)

    async def assign_user(self, registration_id: int, user_id_to_assign: int, current_user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Назначить пользователя на регистрацию проблемы."""
        logger.info("Assigning user to registration", reg_id=registration_id, assignee=user_id_to_assign, assigned_by=current_user_id)
        item = await self.get_by_id(registration_id)
        if not item:
            logger.warning("Registration not found for assignment", reg_id=registration_id)
            return None
            
        await self._service.assign_user_to_document(item.document_id, user_id_to_assign, current_user_id)

        await self._send_chat_notification(
            item.document_id,
            f"👤 Пользователь ID {user_id_to_assign} назначен на регистрацию проблемы {item.track_id}",
        )

        from app.messages.public_services import PublicChatService
        chat_service = PublicChatService(self._service.db)
        try:
            await chat_service.add_participant_by_document(item.document_id, user_id_to_assign)
            logger.debug("User added to chat", user_id=user_id_to_assign, doc_id=item.document_id)
        except ValueError as e:
            logger.debug("User already in chat or cannot be added", user_id=user_id_to_assign, error=str(e))

        logger.info("User assigned successfully", reg_id=registration_id)
        return await self.get_by_id(registration_id)

    async def assign_self(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Назначить себя на регистрацию проблемы."""
        logger.debug("Self-assignment requested", reg_id=registration_id, user_id=user_id)
        return await self.assign_user(registration_id, user_id, user_id)
    
    async def unassign(self, registration_id: int, current_user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Снять назначение с регистрации проблемы."""
        logger.info("Unassigning user from registration", reg_id=registration_id, user_id=current_user_id)
        item = await self.get_by_id(registration_id)
        
        if not item:
            logger.warning("Registration not found for unassignment", reg_id=registration_id)
            return None
            
        if not item.assigned_to: 
            logger.debug("No user assigned, skipping unassignment", reg_id=registration_id)
            return item
        
        # 🔧 Исправлен отсутствующий аргумент в оригинале
        await self._service.doc_service.unassign(item.document_id, current_user_id)

        await self._send_chat_notification(
            item.document_id,
            f"👤 Пользователь снят с регистрации проблемы {item.track_id}",
        )
        logger.info("User unassigned successfully", reg_id=registration_id)
        return await self.get_by_id(registration_id)
    

    async def update_detale(self, registration_id: int, request: ProblemRegistration_DetaleUpdate) -> Optional[ProblemRegistrationResponse]:
        """Обновить детальную информацию регистрации проблемы."""
        logger.info("Updating registration details", reg_id=registration_id)
        item = await self.get_by_id(registration_id)
        if item and item.is_locked:
            logger.warning("Details update blocked: registration is locked", reg_id=registration_id)
            raise ValueError("Редактирование заблокированного документа невозможно")

        # 🔧 Исправлено: вызывается специализированный метод сервиса для детальных обновлений
        result = await self._service.update_response_details(registration_id, request)
        if not result:
            logger.warning("Registration not found during details update", reg_id=registration_id)
            return None

        # Уведомления для деталей обычно не требуются, но при необходимости раскомментируйте:
        # await self._send_chat_notification(...)
        logger.debug("Details updated without notification", reg_id=registration_id)
        return result
    
    async def close(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Метод для закрытия заявки (будет реализован через апдейт статуса)."""
        logger.info("Closing registration requested", reg_id=registration_id, user_id=user_id)
        # TODO: Реализовать смену статуса на CLOSED
        raise NotImplementedError("Метод close() находится в разработке")

    async def change_status(self, registration_id: int, new_status: str, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Изменить статус регистрации."""
        logger.info("Changing registration status", reg_id=registration_id, new_status=new_status, user_id=user_id)
        # TODO: Реализовать валидацию перехода статусов и вызов сервиса
        raise NotImplementedError("Метод change_status() находится в разработке")