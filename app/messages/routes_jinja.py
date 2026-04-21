from typing import List
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse

# from fastapi.templating import Jinja2Templates
# from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from app.core.templates import templates

from pathlib import Path
import os
import uuid

from app.core.database import get_db
from app.auth.routes_jinja import get_current_user_from_cookie, require_auth
from app.auth.models import User
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


@router.get("/messeges")
async def messeges_page(
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

    return templates.TemplateResponse("messeges/index.html", {
        "request": request,
        "chats": chats_result.chats,
        "total": chats_result.total,
        "current_user": current_user,
    })


@router.get("/messeges/{chat_id}")
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
        return RedirectResponse(url="/messeges", status_code=303)

    message_service = PublicMessageService(db)

    # Отмечаем все сообщения как прочитанные
    await message_service.mark_all_as_read(chat_id, user_id=current_user.id)

    messages_result = await message_service.get_chat_messages(
        chat_id=chat_id, user_id=current_user.id, skip=0, limit=200
    )

    # Загружаем список всех чатов для сайдбара с непрочитанными
    chats_result = await chat_service.get_user_chats_with_unread(user_id=current_user.id, skip=0, limit=100)

    return templates.TemplateResponse("messeges/chat.html", {
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


@router.post("/messeges/{chat_id}/send")
async def chat_send(
    request: Request,
    chat_id: int,
    content: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    db=Depends(get_db),
):
    """Отправка сообщения в чат с вложениями."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    if not content.strip() and not files:
        return RedirectResponse(
            url=f"/messeges/{chat_id}?error=Сообщение не может быть пустым",
            status_code=303,
        )

    # Обработка загруженных файлов
    attachments = []
    if files:
        upload_dir = os.path.join("uploads", "attachments")
        os.makedirs(upload_dir, exist_ok=True)

        for file in files:
            if file.filename:
                ext = os.path.splitext(file.filename)[1]
                unique_name = f"{uuid.uuid4().hex}{ext}"
                file_path = os.path.join(upload_dir, unique_name)

                content_bytes = await file.read()
                with open(file_path, "wb") as f:
                    f.write(content_bytes)

                attachments.append(MessageAttachmentCreate(
                    file_path=file_path,
                    original_filename=file.filename,
                    file_type=file.content_type or "application/octet-stream",
                ))

    message_service = PublicMessageService(db)
    try:
        msg = MessageCreate(
            chat_id=chat_id,
            content=content.strip() if content.strip() else "📎 Вложение",
            attachments=attachments if attachments else None,
        )
        await message_service.create(msg, sender_id=current_user.id)
    except Exception as e:
        import logging
        logging.error(f"Ошибка отправки сообщения в чат {chat_id}: {e}", exc_info=True)
        return RedirectResponse(
            url=f"/messeges/{chat_id}?error=Ошибка отправки сообщения: {str(e)}",
            status_code=303,
        )

    return RedirectResponse(url=f"/messeges/{chat_id}", status_code=303)


@router.get("/messeges/attachments/{attachment_id}/download")
async def download_attachment(
    request: Request,
    attachment_id: int,
    db=Depends(get_db),
):
    """Скачать вложение сообщения."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result

    from app.messages.models import MessageAttachment
    from sqlalchemy import select

    result = await db.execute(
        select(MessageAttachment).where(MessageAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment or attachment.is_deleted:
        return RedirectResponse(url="/messeges", status_code=303)

    file_path = attachment.file_path
    if not file_path or not os.path.exists(file_path):
        return RedirectResponse(url="/messeges", status_code=303)

    return FileResponse(
        path=file_path,
        filename=attachment.original_filename or file_path.split(os.sep)[-1],
        media_type=attachment.file_type or "application/octet-stream",
    )
