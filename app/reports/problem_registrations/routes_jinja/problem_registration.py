from typing import List
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from pathlib import Path
from datetime import datetime
import os
import uuid

from app.core.database import get_db
from app.auth.routes_jinja import require_auth
from app.reports.problem_registrations.public_services.problem_registration import PublicProblemRegistrationService
from app.reports.enums import DocumentStage, DocumentStatus

router = APIRouter()

local_templates = Path(__file__).parent.parent / "templates"
global_templates = Path(__file__).parent.parent.parent.parent / "templates"

env = Environment(
    loader=ChoiceLoader([
        FileSystemLoader(str(local_templates)),
        FileSystemLoader(str(global_templates)),
    ]),
    autoescape=True,
)

templates = Jinja2Templates(env=env)


@router.get("/reports/problem-registrations/my")
async def my_problem_registrations_page(
    request: Request,
    page: int = 1,
    db=Depends(get_db),
):
    """Страница моих регистраций проблем (созданных текущим пользователем)."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    skip = (page - 1) * 50

    result = await service.get_my(user_id=current_user.id, skip=skip, limit=50)
    total_pages = max(1, (result.total + 49) // 50)

    return templates.TemplateResponse("my_problem_registrations.html", {
        "request": request,
        "items": result.items,
        "total": result.total,
        "page": page,
        "total_pages": total_pages,
        "current_user": current_user,
    })


@router.get("/reports/problem-registrations")
async def problem_registrations_page(
    request: Request,
    subject: str = "",
    detected_from: str = "",
    detected_to: str = "",
    location_id: int = 0,
    description: str = "",
    nomenclature: str = "",
    track_id: str = "",
    doc_status: str = "",
    doc_type_id: int = 0,
    doc_current_stage: str = "",
    sort_by: str = "id",
    sort_order: str = "desc",
    page: int = 1,
    db=Depends(get_db),
):
    """Страница списка регистраций проблем с фильтрами и сортировкой."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    skip = (page - 1) * 50

    from app.reports.problem_registrations.schemas.problem_registration import ProblemRegistrationFilter
    filters = ProblemRegistrationFilter(
        subject=subject or None,
        detected_from=datetime.fromisoformat(detected_from) if detected_from else None,
        detected_to=datetime.fromisoformat(detected_to + "T23:59:59") if detected_to else None,
        location_id=location_id or None,
        description=description or None,
        nomenclature=nomenclature or None,
        track_id=track_id or None,
        doc_status=doc_status or None,
        doc_type_id=doc_type_id or None,
        doc_current_stage=doc_current_stage or None,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    result = await service.get_all(skip=skip, limit=50, filters=filters)

    total_pages = max(1, (result.total + 49) // 50)

    return templates.TemplateResponse("problem_registrations.html", {
        "request": request,
        "items": result.items,
        "total": result.total,
        "page": page,
        "total_pages": total_pages,
        "current_user": current_user,
        "filters": {
            "subject": subject,
            "detected_from": detected_from,
            "detected_to": detected_to,
            "location_id": location_id,
            "description": description,
            "nomenclature": nomenclature,
            "track_id": track_id,
            "doc_status": doc_status,
            "doc_type_id": doc_type_id,
            "doc_current_stage": doc_current_stage,
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
        "stages": [s.name for s in DocumentStage],
        "statuses": [s.value for s in DocumentStatus],
    })


@router.get("/reports/problem-registrations/create")
async def create_problem_registration_page(
    request: Request,
    db=Depends(get_db),
):
    """Страница создания регистрации проблемы."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    from app.knowledge_base.public_services import PublicLocationService
    location_service = PublicLocationService(db)
    locations = await location_service.get_all(skip=0, limit=1000)

    return templates.TemplateResponse("create_problem_registration.html", {
        "request": request,
        "current_user": current_user,
        "locations": locations.items,
        "statuses": [s.value for s in DocumentStatus],
        "languages": ["ru", "en"],
        "priorities": ["low", "medium", "high", "urgent"],
        "now": datetime.now,
    })


@router.post("/reports/problem-registrations/create")
async def create_problem_registration_post(
    request: Request,
    subject: str = Form(""),
    detected_at: str = Form(""),
    location_id: str = Form(""),
    description: str = Form(""),
    nomenclature: str = Form(""),
    doc_status: str = Form("open"),
    doc_language: str = Form("ru"),
    doc_priority: str = Form("medium"),
    files: List[UploadFile] = File(default=[]),
    db=Depends(get_db),
):
    """Обработка формы создания регистрации проблемы."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    from app.reports.problem_registrations.schemas.problem_registration import ProblemRegistrationCreate
    from app.reports.problem_registrations.public_services.problem_registration import PublicProblemRegistrationService

    service = PublicProblemRegistrationService(db)

    # Конвертируем location_id из строки формы
    loc_id = int(location_id) if location_id and location_id.strip() else 0

    # Парсим detected_at
    parsed_detected_at = None
    if detected_at and detected_at.strip():
        try:
            parsed_detected_at = datetime.fromisoformat(detected_at.strip())
        except (ValueError, TypeError):
            pass

    # Обработка загруженных файлов
    attachment_files = []
    if files:
        upload_dir = os.path.join("uploads", "document_attachments")
        os.makedirs(upload_dir, exist_ok=True)

        for file in files:
            if file.filename:
                ext = os.path.splitext(file.filename)[1]
                unique_name = f"{uuid.uuid4().hex}{ext}"
                file_path = os.path.join(upload_dir, unique_name)

                content_bytes = await file.read()
                with open(file_path, "wb") as f:
                    f.write(content_bytes)

                attachment_files.append({
                    "file_path": file_path,
                    "original_filename": file.filename,
                    "file_type": file.content_type or "application/octet-stream",
                })

    # Безопасная очистка строк
    def clean_str(v):
        return v.strip() if v and v.strip() else None

    try:
        create_data = ProblemRegistrationCreate(
            subject=clean_str(subject),
            detected_at=parsed_detected_at,
            location_id=loc_id or None,
            description=clean_str(description),
            nomenclature=clean_str(nomenclature),
            doc_status=doc_status,
            doc_language=doc_language,
            doc_priority=doc_priority,
            attachment_files=attachment_files if attachment_files else None,
        )
        result = await service.create(create_data, created_by=current_user.id)
        return RedirectResponse(url=f"/reports/problem-registrations/{result.id}", status_code=303)
    except Exception as e:
        from app.knowledge_base.public_services import PublicLocationService
        location_service = PublicLocationService(db)
        locations = await location_service.get_all(skip=0, limit=1000)

        return templates.TemplateResponse("create_problem_registration.html", {
            "request": request,
            "current_user": current_user,
            "locations": locations.items,
            "statuses": [s.value for s in DocumentStatus],
            "languages": ["ru", "en"],
            "priorities": ["low", "medium", "high", "urgent"],
            "error": str(e),
            "form_data": {
                "subject": subject,
                "detected_at": detected_at,
                "location_id": loc_id,
                "description": description,
                "nomenclature": nomenclature,
                "doc_status": doc_status,
                "doc_language": doc_language,
                "doc_priority": doc_priority,
            },
            "now": datetime.now,
        })


@router.get("/reports/problem-registrations/document/{document_id}")
async def view_by_document_page(
    request: Request,
    document_id: int,
    db=Depends(get_db),
):
    """Перенаправление на регистрацию проблемы по ID документа."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_document_id(document_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    return RedirectResponse(url=f"/reports/problem-registrations/{item.id}", status_code=303)


@router.get("/reports/problem-registrations/{registration_id}")
async def view_problem_registration_page(
    request: Request,
    registration_id: int,
    db=Depends(get_db),
):
    """Страница просмотра регистрации проблемы."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=404)

    # Получаем вложения документа
    from app.reports.documents.public_services.document import PublicDocumentService
    doc_service = PublicDocumentService(db)
    attachments = await doc_service.get_attachments(item.document_id)

    # Получаем ID чата по документу
    from app.messeges.public_services import PublicChatService
    chat_service = PublicChatService(db)
    chat_id = await chat_service.get_chat_id_by_document(item.document_id)

    return templates.TemplateResponse("view_problem_registration.html", {
        "request": request,
        "item": item,
        "current_user": current_user,
        "chat_id": chat_id,
        "attachments": attachments,
    })


@router.post("/reports/problem-registrations/{registration_id}/confirm")
async def confirm_problem_registration(
    request: Request,
    registration_id: int,
    db=Depends(get_db),
):
    """Подтверждение регистрации проблемы (блокировка документа)."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    await service.confirm(registration_id, user_id=current_user.id)
    return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)


@router.post("/reports/problem-registrations/{registration_id}/unlock")
async def unlock_problem_registration(
    request: Request,
    registration_id: int,
    db=Depends(get_db),
):
    """Снятие блокировки регистрации проблемы (передача на редактирование)."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    await service.unconfirm(registration_id, user_id=current_user.id)
    return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)


@router.get("/reports/problem-registrations/{registration_id}/edit")
async def edit_problem_registration_page(
    request: Request,
    registration_id: int,
    db=Depends(get_db),
):
    """Страница редактирования регистрации проблемы."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=404)
    if item.is_locked:
        return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)

    from app.knowledge_base.public_services import PublicLocationService
    location_service = PublicLocationService(db)
    locations = await location_service.get_all(skip=0, limit=1000)

    # Получаем вложения документа
    from app.reports.documents.public_services.document import PublicDocumentService
    doc_service = PublicDocumentService(db)
    attachments = await doc_service.get_attachments(item.document_id)

    return templates.TemplateResponse("edit_problem_registration.html", {
        "request": request,
        "item": item,
        "current_user": current_user,
        "locations": locations.items,
        "attachments": attachments,
    })


@router.post("/reports/problem-registrations/{registration_id}/edit")
async def edit_problem_registration_post(
    request: Request,
    registration_id: int,
    subject: str = Form(""),
    detected_at: str = Form(""),
    location_id: str = Form(""),
    description: str = Form(""),
    nomenclature: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    db=Depends(get_db),
):
    """Обработка формы редактирования регистрации проблемы."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    from app.reports.problem_registrations.schemas.problem_registration import ProblemRegistrationUpdate
    from app.reports.problem_registrations.public_services.problem_registration import PublicProblemRegistrationService

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=404)
    if item.is_locked:
        return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)

    # Конвертируем location_id из строки формы
    loc_id = int(location_id) if location_id and location_id.strip() else 0

    # Парсим detected_at
    parsed_detected_at = None
    if detected_at and detected_at.strip():
        try:
            parsed_detected_at = datetime.fromisoformat(detected_at.strip())
        except (ValueError, TypeError):
            pass

    # Обработка загруженных файлов
    attachment_files = []
    if files:
        upload_dir = os.path.join("uploads", "document_attachments")
        os.makedirs(upload_dir, exist_ok=True)

        for file in files:
            if file.filename:
                ext = os.path.splitext(file.filename)[1]
                unique_name = f"{uuid.uuid4().hex}{ext}"
                file_path = os.path.join(upload_dir, unique_name)

                content_bytes = await file.read()
                with open(file_path, "wb") as f:
                    f.write(content_bytes)

                attachment_files.append({
                    "file_path": file_path,
                    "original_filename": file.filename,
                    "file_type": file.content_type or "application/octet-stream",
                })

    try:
        update_data = ProblemRegistrationUpdate(
            subject=subject.strip() or None,
            detected_at=parsed_detected_at,
            location_id=loc_id or None,
            description=description.strip() or None,
            nomenclature=nomenclature.strip() or None,
        )
        await service.update(registration_id, update_data)

        # Добавляем новые вложения к документу
        if attachment_files:
            from app.reports.documents.public_services.document import PublicDocumentService
            doc_service = PublicDocumentService(db)
            for att_data in attachment_files:
                await doc_service.add_attachment(item.document_id, att_data["file_path"], att_data["original_filename"], att_data["file_type"], current_user.id)

        return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)
    except Exception as e:
        from app.knowledge_base.public_services import PublicLocationService
        location_service = PublicLocationService(db)
        locations = await location_service.get_all(skip=0, limit=1000)

        return templates.TemplateResponse("edit_problem_registration.html", {
            "request": request,
            "item": item,
            "current_user": current_user,
            "locations": locations.items,
            "error": str(e),
            "form_data": {
                "subject": subject,
                "detected_at": detected_at,
                "location_id": loc_id,
                "description": description,
                "nomenclature": nomenclature,
            },
        })


@router.get("/reports/documents/attachments/{attachment_id}/download")
async def download_document_attachment(
    attachment_id: int,
    db=Depends(get_db),
):
    """Скачать вложение документа."""
    from app.reports.models import DocumentAttachment
    from sqlalchemy import select

    result = await db.execute(
        select(DocumentAttachment).where(DocumentAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    file_path = attachment.file_path
    if not file_path or not os.path.exists(file_path):
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    return FileResponse(
        path=file_path,
        filename=attachment.original_filename or file_path.split(os.sep)[-1],
        media_type=attachment.file_type or "application/octet-stream",
    )


@router.get("/reports/problem-registrations/{registration_id}/attachments/{attachment_id}/delete")
async def delete_document_attachment(
    request: Request,
    registration_id: int,
    attachment_id: int,
    db=Depends(get_db),
):
    """Удалить вложение документа."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)
    if item.is_locked:
        return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)

    from app.reports.documents.public_services.document import PublicDocumentService
    doc_service = PublicDocumentService(db)
    await doc_service.delete_attachment(attachment_id, user_id=current_user.id)

    return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}/edit", status_code=303)
