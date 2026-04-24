# app\reports\problem_registrations\pr_public_services.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def _send_chat_notification(self, document_id: int, message: str):
        """Отправить уведомление в чат, привязанный к документу."""
        from app.messages.public_services import PublicChatService, PublicMessageService
        chat_service = PublicChatService(self._service.db)
        chat_id = await chat_service.get_chat_id_by_document(document_id)
        if chat_id:
            message_service = PublicMessageService(self._service.db)
            await message_service.send_system_message(chat_id, message)

    async def create(self, request: ProblemRegistrationCreate, created_by: int) -> ProblemRegistrationResponse:
        """Создать регистрацию проблемы. Документ создаётся автоматически."""
        result = await self._service.create(request, created_by=created_by)
        await self._send_chat_notification(
            result.document_id,
            f"📄 Создана новая регистрация проблемы: {result.track_id} — {result.subject or 'Без темы'}",
        )
        return result

    async def get_by_id(self, registration_id: int) -> Optional[ProblemRegistrationResponse]:
        return await self._service.get_by_id(registration_id)

    async def get_by_document_id(self, doc_id: int) -> Optional[ProblemRegistrationResponse]:
        return await self._service.get_by_document_id(doc_id)

    async def get_by_track_id(self, track_id: str) -> Optional[ProblemRegistrationResponse]:
        """Получить регистрацию проблемы по трек-номеру документа."""
        return await self._service.get_by_track_id(track_id)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters=None,
    ) -> ProblemRegistrationListResponse:
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return ProblemRegistrationListResponse(items=result["items"], total=result["total"])

    async def update(self, registration_id: int, request: ProblemRegistrationUpdate) -> Optional[ProblemRegistrationResponse]:
        """Обновить регистрацию проблемы."""
        # Проверяем, заблокирован ли документ
        item = await self.get_by_id(registration_id)
        if item and item.is_locked:
            raise ValueError("Редактирование заблокированного документа невозможно")

        result = await self._service.update(registration_id, request)
        if not result:
            return None

        # Формируем описание изменений для уведомления
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
        return result

    async def confirm(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Подтвердить регистрацию проблемы (заблокировать документ)."""
        item = await self.get_by_id(registration_id)
        if not item:
            return None

        if item.is_locked:
            return item  # Уже заблокирован

        from app.reports.documents.document_public_service import PublicDocumentService
        doc_service = PublicDocumentService(self._service.db)
        await doc_service.lock(item.document_id, user_id=user_id)
        
        await self._send_chat_notification(
            item.document_id,
            f"🔒 Регистрация проблемы {item.track_id} подтверждена и заблокирована",
        )

        # Возвращаем обновлённую регистрацию
        return await self.get_by_id(registration_id)

    async def unconfirm(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Снять блокировку регистрации проблемы (разблокировать документ)."""
        item = await self.get_by_id(registration_id)
        if not item:
            return None
        if not item.is_locked:
            return item  # Уже разблокирован

        from app.reports.documents.document_public_service import PublicDocumentService
        doc_service = PublicDocumentService(self._service.db)
        await doc_service.unlock(item.document_id, user_id=user_id)

        await self._send_chat_notification(
            item.document_id,
            f"🔓 Регистрация проблемы {item.track_id} передана на редактирование",
        )

        # Возвращаем обновлённую регистрацию
        return await self.get_by_id(registration_id)

    async def delete(self, registration_id: int) -> bool:
        """Удалить регистрацию проблемы."""
        item = await self.get_by_id(registration_id)
        if item:
            await self._send_chat_notification(
                item.document_id,
                f"🗑️ Регистрация проблемы {item.track_id} удалена",
            )
        return await self._service.delete(registration_id)

    async def get_my(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> ProblemRegistrationListResponse:
        """Получить список регистраций, созданных пользователем."""
        from app.reports.problem_registrations.pr_schemas import ProblemRegistrationFilter
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
        filters = ProblemRegistrationFilter(
            assigned_to=user_id,
            sort_by="id",
            sort_order="desc",
        )
        result = await self._service.get_all(skip=skip, limit=limit, filters=filters)
        return ProblemRegistrationListResponse(items=result["items"], total=result["total"])

    async def archive(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Архивировать регистрацию проблемы."""
        item = await self.get_by_id(registration_id)
        if not item:
            return None
        await self._service.archive_document(item.document_id, user_id=user_id)
        await self._send_chat_notification(
            item.document_id,
            f"📦 Регистрация проблемы {item.track_id} архивирована",
        )
        return await self.get_by_id(registration_id)

    async def unarchive(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Восстановить регистрацию проблемы из архива."""
        item = await self.get_by_id(registration_id)
        if not item:
            return None
        await self._service.unarchive_document(item.document_id, user_id=user_id)
        await self._send_chat_notification(
            item.document_id,
            f"📦 Регистрация проблемы {item.track_id} восстановлена из архива",
        )
        return await self.get_by_id(registration_id)

    async def assign_user(self, registration_id: int, user_id_to_assign: int, current_user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Назначить пользователя на регистрацию проблемы."""
        item = await self.get_by_id(registration_id)
        print("asaasa")
        if not item:
            return None
        await self._service.assign_user_to_document(item.document_id, user_id_to_assign, current_user_id)

        # Отправляем уведомление в чат
        await self._send_chat_notification(
            item.document_id,
            f"👤 Пользователь ID {user_id_to_assign} назначен на регистрацию проблемы {item.track_id}",
        )

        # Добавляем пользователя в чат, привязанный к документу
        from app.messages.public_services import PublicChatService
        chat_service = PublicChatService(self._service.db)
        try:
            await chat_service.add_participant_by_document(item.document_id, user_id_to_assign)
        except ValueError:
            pass  # Пользователь уже участник — это не ошибка

        return await self.get_by_id(registration_id)

    async def assign_self(self, registration_id: int, user_id: int) -> Optional[ProblemRegistrationResponse]:
        """Назначить себя на регистрацию проблемы."""
        return await self.assign_user(registration_id, user_id, user_id)
    
    async def unassign(self, registration_id: int, current_user_id: int) -> Optional[ProblemRegistrationResponse]:
        item = await self.get_by_id(registration_id)
        
        if not item:
            return None
        
                # Если никто не назначен, можно сразу выйти или обработать логику по желанию
        if not item.assigned_to: 
            return item
        
        from app.reports.documents.document_public_service import PublicDocumentService
        doc_service = PublicDocumentService(self._service.db)
        await doc_service.unassign(item.document_id, )

        await self._send_chat_notification(
            item.document_id,
            f"👤 Пользователь снят с регистрации проблемы {item.track_id}",
        )
        return await self.get_by_id(registration_id)
    

    async def update_detale(self, registration_id: int, request: ProblemRegistration_DetaleUpdate) -> Optional[ProblemRegistrationResponse]:
        """Обновить регистрацию проблемы."""
        # Проверяем, заблокирован ли документ
        item = await self.get_by_id(registration_id)
        if item and item.is_locked:
            raise ValueError("Редактирование заблокированного документа невозможно")

        result = await self._service.update(registration_id, request)
        if not result:
            return None

        # Формируем описание изменений для уведомления
        changes = []
        # update_data = request.model_dump(exclude_unset=True)
        # if update_data.get("subject"):
        #     changes.append(f"Тема: {update_data['subject']}")
        # if update_data.get("description"):
        #     changes.append("Описание изменено")
        # if update_data.get("nomenclature"):
        #     changes.append(f"Номенклатура: {update_data['nomenclature']}")
        # if update_data.get("detected_at"):
        #     changes.append("Дата обнаружения изменена")
        # if update_data.get("location_id"):
        #     changes.append("Локация изменена")

        if changes:
            await self._send_chat_notification(
                result.document_id,
                f"✏️ Регистрация проблемы {result.track_id} обновлена: {'; '.join(changes)}",
            )
        return result
    
    async def close():
        """Метод для закрытия заявки"""
        """Будкт реализован через абдейт сервиса"""
        pass

    async def change_status():
        pass