from typing import Optional, List
from datetime import datetime
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user, oauth2_scheme
from app.auth.models import User
from app.messeges.schemas.chat import (
    ChatCreate, ChatUpdate, ChatResponse, ChatListResponse, ChatFilter,
)
from app.messeges.schemas.message import (
    MessageCreate, MessageResponse, MessageListResponse,
    MessageReadResponse, MessageAttachmentCreate, MessageAttachmentResponse,
)
from app.admin.messages.services import AdminMessageService

router = APIRouter(
    prefix="/admin",
    tags=["Admin — Messages"],
    dependencies=[Depends(oauth2_scheme)],
)


def _get_service(db: AsyncSession = Depends(get_db)) -> AdminMessageService:
    return AdminMessageService(db)


# --- Chats ---

@router.post("/chats", response_model=ChatResponse, summary="Создать чат", status_code=201)
async def create_chat(
    request: ChatCreate, creator_id: int,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    return await svc.create_chat(request, creator_id)


@router.get("/chats/{chat_id}", response_model=ChatResponse, summary="Чат по ID")
async def get_chat(
    chat_id: int, current_user: User = Depends(get_current_user),
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    chat = await svc.get_chat(chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return chat


@router.get("/chats", response_model=ChatListResponse, summary="Все чаты с фильтрами")
async def list_chats(
    participant_id: Optional[int] = None,
    document_id: Optional[int] = None,
    name: Optional[str] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    sort_by: Optional[str] = "updated_at",
    sort_order: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 100,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    """Все чаты с фильтрами и сортировкой."""
    filters = ChatFilter(
        participant_id=participant_id,
        document_id=document_id,
        name=name,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await svc.list_all_chats(filters=filters, skip=skip, limit=limit)


@router.get("/users/{user_id}/chats", response_model=ChatListResponse, summary="Чаты пользователя")
async def list_user_chats(
    user_id: int, skip: int = 0, limit: int = 100,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    """Все чаты пользователя (обёртка)."""
    return await svc.list_user_chats(user_id, skip, limit)


@router.put("/chats/{chat_id}", response_model=ChatResponse, summary="Обновить чат")
async def update_chat(
    chat_id: int, request: ChatUpdate,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    return await svc.update_chat(chat_id, request)


@router.delete("/chats/{chat_id}", summary="Удалить чат")
async def delete_chat(
    chat_id: int,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    result = await svc.delete_chat(chat_id)
    if not result:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return {"chat_id": chat_id, "action": "deleted"}


@router.get("/chats/{chat_id}/unread", summary="Счётчик непрочитанных")
async def get_unread_count(
    chat_id: int, current_user: User = Depends(get_current_user),
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    count = await svc.get_unread_count(chat_id, current_user.id)
    return {"chat_id": chat_id, "user_id": current_user.id, "unread_count": count}


# --- Messages ---

@router.post(
    "/messages/upload",
    response_model=MessageResponse,
    summary="Создать сообщение с файлами",
    status_code=201,
)
async def create_message_with_files(
    chat_id: int,
    content: str,
    sender_id: int,
    files: List[UploadFile] = File(default=[]),
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    """Создать сообщение с загрузкой файлов."""
    from app.messeges.schemas.message import MessageCreate, MessageAttachmentCreate

    attachments = []
    if files:
        upload_dir = os.path.join("uploads", "attachments")
        os.makedirs(upload_dir, exist_ok=True)

        for file in files:
            ext = os.path.splitext(file.filename or "")[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(upload_dir, unique_name)

            content_bytes = await file.read()
            with open(file_path, "wb") as f:
                f.write(content_bytes)

            attachments.append(MessageAttachmentCreate(
                file_path=file_path,
                file_type=file.content_type or "application/octet-stream",
            ))

    request = MessageCreate(
        chat_id=chat_id,
        content=content,
        attachments=attachments if attachments else None,
    )
    return await svc.create_message(request, sender_id)


@router.post("/messages", response_model=MessageResponse, summary="Создать сообщение", status_code=201)
async def create_message(
    request: MessageCreate, sender_id: int,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    """Создать сообщение (без загрузки файлов, только пути)."""
    return await svc.create_message(request, sender_id)


@router.get("/messages/{message_id}", response_model=MessageResponse, summary="Сообщение по ID")
async def get_message(
    message_id: int,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    msg = await svc.get_message(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    return msg


@router.get("/chats/{chat_id}/messages", response_model=MessageListResponse, summary="Сообщения чата")
async def list_chat_messages(
    chat_id: int, current_user: User = Depends(get_current_user), skip: int = 0, limit: int = 100,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    return await svc.list_chat_messages(chat_id, current_user.id, skip, limit)


@router.post("/messages/{message_id}/read", response_model=MessageReadResponse, summary="Отметить прочитанным")
async def mark_read(
    message_id: int, current_user: User = Depends(get_current_user),
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    return await svc.mark_read(message_id, current_user.id)


@router.post("/chats/{chat_id}/read-all", summary="Отметить все прочитанными")
async def mark_all_read(
    chat_id: int, current_user: User = Depends(get_current_user),
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    count = await svc.mark_all_read(chat_id, current_user.id)
    return {"chat_id": chat_id, "user_id": current_user.id, "marked_count": count}


@router.delete("/messages/{message_id}", summary="Удалить сообщение")
async def delete_message(
    message_id: int,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    result = await svc.delete_message(message_id)
    if not result:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    return {"message_id": message_id, "action": "deleted"}


@router.post("/messages/{message_id}/attachments", response_model=MessageAttachmentResponse,
             summary="Добавить вложение (путь)", status_code=201)
async def add_attachment(
    message_id: int, request: MessageAttachmentCreate,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    return await svc.add_attachment(message_id, request.file_path, request.file_type)


@router.post("/messages/{message_id}/upload", response_model=MessageAttachmentResponse,
             summary="Загрузить файл как вложение", status_code=201)
async def upload_attachment(
    message_id: int,
    file: UploadFile = File(...),
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    """Загрузка реального файла и прикрепление к сообщению."""
    # Создаём директорию для загрузок
    upload_dir = os.path.join("uploads", "attachments")
    os.makedirs(upload_dir, exist_ok=True)

    # Генерируем уникальное имя файла
    ext = os.path.splitext(file.filename or "")[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, unique_name)

    # Сохраняем файл
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Определяем тип файла
    file_type = file.content_type or "application/octet-stream"

    return await svc.add_attachment(message_id, file_path, file_type)


@router.delete("/attachments/{attachment_id}", summary="Удалить вложение")
async def delete_attachment(
    attachment_id: int,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    result = await svc.delete_attachment(attachment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Вложение не найдено")
    return {"attachment_id": attachment_id, "action": "deleted"}


@router.get(
    "/messages/{message_id}/attachments",
    response_model=List[MessageAttachmentResponse],
    summary="Вложения сообщения",
)
async def get_message_attachments(
    message_id: int,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    """Все вложения сообщения."""
    return await svc.get_attachments_by_message(message_id)


@router.get(
    "/attachments/{attachment_id}",
    response_model=MessageAttachmentResponse,
    summary="Вложение по ID",
)
async def get_attachment(
    attachment_id: int,
    _admin=Depends(require_admin),
    svc: AdminMessageService = Depends(_get_service),
):
    """Вложение по ID."""
    attachment = await svc.get_attachment(attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Вложение не найдено")
    return attachment
