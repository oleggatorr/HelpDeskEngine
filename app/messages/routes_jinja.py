from typing import List
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse

from app.core.storage.local_storage import LocalFileStorage
from app.core.storage.file_storage import FileStorage
from app.messages.message_attachment_service import MessageAttachmentService

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

# from fastapi.templating import Jinja2Templates
# from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from app.core.templates import templates

from pathlib import Path
import os
import uuid

from app.core.database import get_db
from app.auth.routes_jinja import require_auth
from app.messages.public_services import PublicChatService, PublicMessageService
from app.messages.schemas import MessageCreate, MessageAttachmentCreate

router = APIRouter()

local_templates = Path(__file__).parent / "templates"
global_templates = Path(__file__).parent.parent / "templates"

# env = Environment(
#     loader=ChoiceLoader([
#         FileSystemLoader(str(local_templates)),
#         FileSystemLoader(str(global_templates)),
#     ]),
#     autoescape=True,
# )

# templates = Jinja2Templates(env=env)

def get_file_storage() -> FileStorage:
    """Factory для хранилища — легко заменить на S3/MinIO в будущем."""
    return LocalFileStorage(base_path="uploads/attachments")

async def get_attachment_service(
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage)
) -> MessageAttachmentService:
    return MessageAttachmentService(db=db, storage=storage)


@router.get("/messages")
async def messages_page(
    request: Request,
    db=Depends(get_db),
):
    """Страница сообщений со списком чатов пользователя."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicChatService(db)
    chats_result = await service.get_user_chats_with_unread(user_id=current_user.id, skip=0, limit=100)

    return templates.TemplateResponse("messages/index.html", {
        "request": request,
        "chats": chats_result.chats,
        "total": chats_result.total,
        "current_user": current_user,
    })


@router.get("/messages/{chat_id}")
async def chat_page(
    request: Request,
    chat_id: int,
    error: str = "",
    db=Depends(get_db),
):
    """Страница чата с сообщениями."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    chat_service = PublicChatService(db)
    chat = await chat_service.get_by_id(chat_id, user_id=current_user.id)
    if not chat:
        return RedirectResponse(url="/messages", status_code=303)

    message_service = PublicMessageService(db)

    # Отмечаем все сообщения как прочитанные
    await message_service.mark_all_as_read(chat_id, user_id=current_user.id)

    messages_result = await message_service.get_chat_messages(
        chat_id=chat_id, user_id=current_user.id, skip=0, limit=200
    )

    # Загружаем список всех чатов для сайдбара с непрочитанными
    chats_result = await chat_service.get_user_chats_with_unread(user_id=current_user.id, skip=0, limit=100)

    return templates.TemplateResponse("messages/chat.html", {
        "request": request,
        "chat": chat,
        "messages": messages_result.messages,
        "chats": chats_result.chats,
        "total": chats_result.total,
        "current_user": current_user,
        "error": error,
        "access_token": request.cookies.get("access_token", ""),
        "chat_name": chat.name or "",
    })


@router.post("/messages/{chat_id}/send")
async def chat_send(
    request: Request,
    chat_id: int,
    content: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    attachment_service: MessageAttachmentService = Depends(get_attachment_service),
):
    """Отправка сообщения в чат с вложениями: сначала сообщение, потом файлы."""
    
    # 🔐 Авторизация
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    # 📝 Валидация
    if not content.strip() and not files:
        return RedirectResponse(
            url=f"/messages/{chat_id}?error=Сообщение не может быть пустым",
            status_code=303,
        )

    message_service = PublicMessageService(db)
    
    try:
        # ✅ ШАГ 1: Создаём сообщение (пока без вложений)
        msg = MessageCreate(
            chat_id=chat_id,
            content=content.strip() if content.strip() else "📎 Вложение",
            # attachments пока не передаём — создадим их после
        )
        created_message = await message_service.create(msg, sender_id=current_user.id)
        message_id = created_message.id  # ← получили ID нового сообщения
        
        # ✅ ШАГ 2: Загружаем файлы и привязываем к сообщению
        for file in files:
            if file.filename:
                content_bytes = await file.read()
                
                await attachment_service.upload(
                    message_id=message_id,  # ← теперь есть куда привязать
                    content=content_bytes,
                    filename=file.filename,
                    user_id=current_user.id,
                    file_type=file.content_type or "application/octet-stream",
                )
        
        # ✅ Коммит всех изменений (сообщение + вложения)
        await db.commit()
        
    except Exception as e:
        await db.rollback()  # ← откат и сообщения, и вложений при ошибке
        logger.error(f"Ошибка отправки сообщения в чат {chat_id}: {e}", exc_info=True)
        return RedirectResponse(
            url=f"/messages/{chat_id}?error=Ошибка отправки: {str(e)}",
            status_code=303,
        )

    return RedirectResponse(url=f"/messages/{chat_id}", status_code=303)


@router.get("/messages/attachments/{attachment_id}/download")
async def download_attachment(
    request: Request,
    attachment_id: int,
    db=Depends(get_db),
):
    """Открытие/скачивание вложения сообщения."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result

    from app.messages.models import MessageAttachment
    from sqlalchemy import select
    from pathlib import Path

    result = await db.execute(
        select(MessageAttachment).where(MessageAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment or getattr(attachment, "is_deleted", False):
        return RedirectResponse(url="/messages", status_code=303)

    file_path = attachment.file_path
    if not file_path or not Path(file_path).exists():
        return RedirectResponse(url="/messages", status_code=303)
    return FileResponse(
        path=file_path,
        filename=attachment.original_filename or Path(file_path).name,
        media_type=attachment.file_type or "application/octet-stream",
        content_disposition_type="inline",  # ← Браузер откроет файл, если умеет
    )
