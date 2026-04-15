from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.auth.models import User
from app.messeges.public_services import PublicChatService, PublicMessageService
from app.messeges.schemas import (
    ChatCreate,
    ChatResponse,
    ChatListResponse,
    ChatUpdate,
    ChatFilter,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    MessageReadResponse,
    MessageAttachmentCreate,
    MessageAttachmentResponse,
)

router = APIRouter()

local_templates = Path(__file__).parent / "templates"
global_templates = Path(__file__).parent.parent / "templates"

env = Environment(
    loader=ChoiceLoader([
        FileSystemLoader(str(local_templates)),
        FileSystemLoader(str(global_templates)),
    ]),
    autoescape=True,
)

templates = Jinja2Templates(env=env)


def _get_public_chat_service(db: AsyncSession = Depends(get_db)) -> PublicChatService:
    return PublicChatService(db)


def _get_public_message_service(db: AsyncSession = Depends(get_db)) -> PublicMessageService:
    return PublicMessageService(db)


# ==========================================
# CHAT ROUTES
# ==========================================

@router.post(
    "/chats",
    response_model=ChatResponse,
    summary="Создать чат",
    status_code=status.HTTP_201_CREATED,
)
async def create_chat(
    request: ChatCreate,
    current_user: User = Depends(get_current_user),
    service: PublicChatService = Depends(_get_public_chat_service),
):
    """Создание чата с участниками. Создатель автоматически добавляется."""
    return await service.create(request, creator_id=current_user.id)


@router.get(
    "/chats/{chat_id}",
    response_model=ChatResponse,
    summary="Получить чат по ID",
)
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicChatService = Depends(_get_public_chat_service),
):
    """Получить информацию о чате. Только для участников."""
    chat = await service.get_by_id(chat_id, user_id=current_user.id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
    return chat


@router.get(
    "/chats",
    response_model=ChatListResponse,
    summary="Список чатов пользователя",
)
async def list_chats(
    skip: int = 0,
    limit: int = 100,
    filters: ChatFilter = Depends(),
    current_user: User = Depends(get_current_user),
    service: PublicChatService = Depends(_get_public_chat_service),
):
    """Все чаты текущего пользователя с фильтрами и пагинацией."""
    if filters.participant_id is None:
        filters.participant_id = current_user.id
    return await service.list_all(filters, skip=skip, limit=limit)


@router.put(
    "/chats/{chat_id}",
    response_model=ChatResponse,
    summary="Обновить чат",
)
async def update_chat(
    chat_id: int,
    request: ChatUpdate,
    current_user: User = Depends(get_current_user),
    service: PublicChatService = Depends(_get_public_chat_service),
):
    """Обновить название чата, добавить/удалить участников."""
    return await service.update(chat_id, request, remover_id=current_user.id)


@router.delete(
    "/chats/{chat_id}",
    summary="Удалить чат",
)
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicChatService = Depends(_get_public_chat_service),
):
    """Удалить чат."""
    result = await service.delete(chat_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
    return {"success": result}


@router.get(
    "/chats/{chat_id}/unread-count",
    summary="Количество непрочитанных сообщений",
)
async def get_unread_count(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicChatService = Depends(_get_public_chat_service),
):
    """Количество непрочитанных сообщений в чате для текущего пользователя."""
    count = await service.get_unread_count(chat_id, user_id=current_user.id)
    return {"chat_id": chat_id, "unread_count": count}


# ==========================================
# MESSAGE ROUTES
# ==========================================

@router.post(
    "/chats/{chat_id}/messages",
    response_model=MessageResponse,
    summary="Отправить сообщение",
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    chat_id: int,
    request: MessageCreate,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Отправить сообщение в чат от имени текущего пользователя."""
    if request.chat_id != chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_id в URL и теле запроса не совпадают",
        )
    return await service.create(request, sender_id=current_user.id)


@router.post(
    "/chats/{chat_id}/messages/with-files",
    response_model=MessageResponse,
    summary="Отправить сообщение с файлами",
    status_code=status.HTTP_201_CREATED,
)
async def create_message_with_files(
    chat_id: int,
    content: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Отправить сообщение в чат с загрузкой файлов."""
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

    request = MessageCreate(
        chat_id=chat_id,
        content=content,
        attachments=attachments if attachments else None,
    )
    return await service.create(request, sender_id=current_user.id)


@router.get(
    "/chats/{chat_id}/messages",
    response_model=MessageListResponse,
    summary="Сообщения чата",
)
async def get_chat_messages(
    chat_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Сообщения чата с пагинацией."""
    return await service.get_chat_messages(
        chat_id=chat_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/chats/{chat_id}/messages/fragment",
    response_class=HTMLResponse,
    summary="HTML-фрагмент сообщений чата (для автообновления)",
)
async def get_chat_messages_fragment(
    request: Request,
    chat_id: int,
    skip: int = 0,
    limit: int = 200,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Возвращает HTML-фрагмент сообщений для автообновления без перезагрузки страницы."""
    messages_result = await service.get_chat_messages(
        chat_id=chat_id, user_id=current_user.id, skip=skip, limit=limit
    )
    return templates.TemplateResponse("messeges/chat_messages_fragment.html", {
        "request": request,
        "messages": messages_result.messages,
        "current_user": current_user,
        "error": None,
    })


@router.get(
    "/chats/sidebar/fragment",
    response_class=HTMLResponse,
    summary="HTML-фрагмент сайдбара чатов (для автообновления)",
)
async def get_chat_sidebar_fragment(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Возвращает HTML-фрагмент сайдбара чатов для автообновления."""
    chat_service = PublicChatService(db)
    chats_result = await chat_service.get_user_chats_with_unread(
        user_id=current_user.id, skip=skip, limit=limit
    )
    return templates.TemplateResponse("messeges/chat_list.html", {
        "request": request,
        "chats": chats_result.chats,
        "total": chats_result.total,
        "current_user": current_user,
    })


@router.get(
    "/messages/{message_id}",
    response_model=MessageResponse,
    summary="Получить сообщение по ID",
)
async def get_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Получить сообщение по ID."""
    message = await service.get_by_id(message_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")
    return message


@router.post(
    "/messages/{message_id}/read",
    response_model=MessageReadResponse,
    summary="Отметить сообщение как прочитанное",
)
async def mark_as_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Отметить сообщение как прочитанное текущим пользователем."""
    return await service.mark_as_read(message_id, user_id=current_user.id)


@router.post(
    "/chats/{chat_id}/messages/read-all",
    summary="Отметить все сообщения как прочитанные",
)
async def mark_all_as_read(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Отметить все сообщения в чате как прочитанные."""
    count = await service.mark_all_as_read(chat_id, user_id=current_user.id)
    return {"chat_id": chat_id, "marked_read": count}


@router.delete(
    "/messages/{message_id}",
    summary="Удалить сообщение",
)
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Удалить сообщение."""
    result = await service.delete(message_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")
    return {"success": result}


# ==========================================
# ATTACHMENT ROUTES
# ==========================================

@router.post(
    "/messages/{message_id}/attachments",
    response_model=MessageAttachmentResponse,
    summary="Добавить вложение",
    status_code=status.HTTP_201_CREATED,
)
async def add_attachment(
    message_id: int,
    file_path: str,
    original_filename: Optional[str] = None,
    file_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Добавить вложение к сообщению."""
    return await service.add_attachment(message_id, file_path, original_filename, file_type)


@router.get(
    "/messages/{message_id}/attachments",
    response_model=list[MessageAttachmentResponse],
    summary="Все вложения сообщения",
)
async def get_attachments(
    message_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Получить все вложения сообщения."""
    return await service.get_attachments_by_message(message_id)


@router.get(
    "/attachments/{attachment_id}",
    response_model=MessageAttachmentResponse,
    summary="Получить вложение по ID",
)
async def get_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Получить вложение по ID."""
    attachment = await service.get_attachment(attachment_id)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вложение не найдено")
    return attachment


@router.delete(
    "/attachments/{attachment_id}",
    summary="Удалить вложение",
)
async def delete_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    service: PublicMessageService = Depends(_get_public_message_service),
):
    """Удалить вложение."""
    result = await service.delete_attachment(attachment_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вложение не найдено")
    return {"success": result}


@router.get("/", summary="Messages модуль")
async def messages_root():
    return {"message": "Messages module"}


# === Архив ===
@router.post("/chats/{chat_id}/archive", response_model=ChatResponse, summary="Архивировать чат")
async def archive_chat(chat_id: int, current_user: User = Depends(get_current_user), service: PublicChatService = Depends(_get_public_chat_service)):
    try: return await service.archive(chat_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/chats/{chat_id}/unarchive", response_model=ChatResponse, summary="Разархивировать чат")
async def unarchive_chat(chat_id: int, current_user: User = Depends(get_current_user), service: PublicChatService = Depends(_get_public_chat_service)):
    try: return await service.unarchive(chat_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# === Закрытие/Открытие ===
@router.post("/chats/{chat_id}/close", response_model=ChatResponse, summary="Закрыть чат")
async def close_chat(chat_id: int, current_user: User = Depends(get_current_user), service: PublicChatService = Depends(_get_public_chat_service)):
    try: return await service.close(chat_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/chats/{chat_id}/open", response_model=ChatResponse, summary="Открыть чат")
async def open_chat(chat_id: int, current_user: User = Depends(get_current_user), service: PublicChatService = Depends(_get_public_chat_service)):
    try: return await service.open(chat_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# === Анонимизация ===
@router.post("/chats/{chat_id}/anonymize", response_model=ChatResponse, summary="Анонимизировать чат")
async def anonymize_chat(chat_id: int, current_user: User = Depends(get_current_user), service: PublicChatService = Depends(_get_public_chat_service)):
    try: return await service.anonymize(chat_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/chats/{chat_id}/deanonymize", response_model=ChatResponse, summary="Деанонимизировать чат")
async def deanonymize_chat(chat_id: int, current_user: User = Depends(get_current_user), service: PublicChatService = Depends(_get_public_chat_service)):
    try: return await service.deanonymize(chat_id, current_user.id)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# === Участники ===
@router.post("/chats/{chat_id}/add-participant", response_model=ChatResponse, summary="Добавить участника")
async def add_participant(chat_id: int, request: dict, current_user: User = Depends(get_current_user), service: PublicChatService = Depends(_get_public_chat_service)):
    """Добавить пользователя в чат по user_id."""
    from app.messeges.schemas import ChatUpdate
    user_id = request.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id обязателен")
    try: return await service.update(chat_id, ChatUpdate(add_participant_ids=[user_id]))
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/chats/{chat_id}/leave", response_model=ChatResponse, summary="Покинуть чат")
async def leave_chat(chat_id: int, current_user: User = Depends(get_current_user), service: PublicChatService = Depends(_get_public_chat_service)):
    """Покинуть чат (удалить себя из участников)."""
    from app.messeges.schemas import ChatUpdate
    try: return await service.update(chat_id, ChatUpdate(remove_participant_ids=[current_user.id]))
    except ValueError as e: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/chats/mark-all-read", summary="Отметить все чаты прочитанными")
async def mark_all_chats_read(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Отметить все сообщения во всех чатах пользователя как прочитанные."""
    from app.messeges.public_services import PublicMessageService
    from app.messeges.public_services import PublicChatService
    chat_service = PublicChatService(db)
    message_service = PublicMessageService(db)
    chats_result = await chat_service.get_user_chats(user_id=current_user.id, skip=0, limit=1000)
    total = 0
    for chat in chats_result.chats:
        total += await message_service.mark_all_as_read(chat.id, user_id=current_user.id)
    return {"marked_read": total}
