from typing import List
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse

# from fastapi.templating import Jinja2Templates
# from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from app.core.templates import templates

from pathlib import Path
from datetime import datetime
import os
import uuid

from app.core.database import get_db
from app.auth.routes_jinja import require_auth
from app.reports.problem_registrations.pr_public_services import PublicProblemRegistrationService
from app.reports.documents.document_models import DocumentStage, DocumentLanguage, DocumentPriority, DocumentStatus

router = APIRouter()

local_templates = Path(__file__).parent.parent / "templates"
global_templates = Path(__file__).parent.parent.parent.parent / "templates"

# env = Environment(
#     loader=ChoiceLoader([
#         FileSystemLoader(str(local_templates)),
#         FileSystemLoader(str(global_templates)),
#     ]),
#     autoescape=True,
# )

# templates = Jinja2Templates(env=env)


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


@router.get("/reports/problem-registrations/assigned")
async def assigned_registration_page(
    request: Request,
    page: int = 1,
    db=Depends(get_db),):
    """Страница назначенных регистраций проблем на текущего пользователя."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    skip = (page - 1) * 50

    result = await service.get_assigned(user_id=current_user.id, skip=skip, limit=50)
    total_pages = max(1, (result.total + 49) // 50)
    return templates.TemplateResponse("assigned_problem_registrations.html",{
        "request": request,
        "items": result.items,
        "total": result.total,
        "page": page,
        "total_pages": total_pages,
        "current_user": current_user,
    })

@router.get("/reports/problem-registrations/admin_list")
async def problem_registrations_admin_list_page(
    request: Request,
    # 🔹 ProblemRegistration фильтры
    subject: str = "",
    detected_from: str = "",
    detected_to: str = "",
    location_id: str = "",
    description: str = "",
    nomenclature: str = "",
    approved_from: str = "",
    approved_to: str = "",
    action: str = "",
    responsible_department_id: str = "",
    comment: str = "",
    # 🔹 Document фильтры
    track_id: str = "",
    doc_created_from: str = "",
    doc_created_to: str = "",
    doc_status: str = "",
    doc_type_id: str = "",
    doc_current_stage: str = "",
    created_by: str = "",
    assigned_to: str = "",
    is_locked: str = "",  # 🔒 Новое поле
    # 🔹 Сортировка и пагинация
    sort_by: str = "id",
    sort_order: str = "desc",
    page: int = 1,
    db=Depends(get_db),
    
):
    """Админ-страница списка регистраций проблем с ПОЛНОЙ фильтрацией."""
    # 🔐 Авторизация
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    skip = (page - 1) * 50

    # 🔽 Хелперы для безопасной конвертации
    def to_int_or_none(val: str) -> int | None:
        if not val or not val.strip():
            return None
        try:
            return int(val.strip())
        except (ValueError, TypeError):
            return None

    def to_bool_or_none(val: str) -> bool | None:
        if not val or not val.strip():
            return None
        return val.strip().lower() in ("true", "1", "yes", "on")
    

    def parse_date(val: str, end_of_day: bool = False) -> datetime | None:
        if not val or not val.strip():
            return None
        try:
            dt = datetime.fromisoformat(val)
            if end_of_day:
                return dt.replace(hour=23, minute=59, second=59)
            return dt
        except (ValueError, TypeError):
            return None

    # 📦 Сборка фильтров
    from app.reports.problem_registrations.pr_schemas import ProblemRegistrationFilter
    from app.reports.problem_registrations.pr_models import ProblemAction
    from app.reports.documents.document_models import DocumentStatus

    filters = ProblemRegistrationFilter(
        # ProblemRegistration поля
        subject=subject or None,
        detected_from=parse_date(detected_from),
        detected_to=parse_date(detected_to, end_of_day=True),
        location_id=to_int_or_none(location_id),
        description=description or None,
        nomenclature=nomenclature or None,
        approved_from=parse_date(approved_from),
        approved_to=parse_date(approved_to, end_of_day=True),
        action=action or None,  # валидатор схемы обработает строку
        responsible_department_id=to_int_or_none(responsible_department_id),
        comment=comment or None,
        
        # Document поля
        track_id=track_id or None,
        doc_created_from=parse_date(doc_created_from),
        doc_created_to=parse_date(doc_created_to, end_of_day=True),
        doc_status=doc_status or None,  # валидатор схемы обработает строку
        doc_type_id=to_int_or_none(doc_type_id),
        doc_current_stage=doc_current_stage or None,
        created_by=to_int_or_none(created_by),
        assigned_to=to_int_or_none(assigned_to),
        is_locked=to_bool_or_none(is_locked),  # 🔒 Конвертация строки в bool
        
        # Сортировка
        sort_by=sort_by,
        sort_order=sort_order,
    )

    result = await service.get_all(skip=skip, limit=50, filters=filters)
    total_pages = max(1, (result.total + 49) // 50)
    from app.knowledge_base.public_services import PublicDepartmentService
    PDS = PublicDepartmentService(db)
    departments = await PDS.get_all()
    print(list(departments.items))

    # 🎨 Подготовка контекста для шаблона
    return templates.TemplateResponse("problem_registrations_admin.html", {
        "request": request,
        "items": result.items,
        "total": result.total,
        "page": page,
        "total_pages": total_pages,
        "current_user": current_user,
        "departments": departments.items,
        
        # 🔁 Сохраняем ВСЕ фильтры для отображения в форме
        "filters": {
            "subject": subject,
            "detected_from": detected_from,
            "detected_to": detected_to,
            "location_id": location_id,
            "description": description,
            "nomenclature": nomenclature,
            "approved_from": approved_from,
            "approved_to": approved_to,
            "action": action,
            "responsible_department_id": responsible_department_id,
            "comment": comment,
            "track_id": track_id,
            "doc_created_from": doc_created_from,
            "doc_created_to": doc_created_to,
            "doc_status": doc_status,
            "doc_type_id": doc_type_id,
            "doc_current_stage": doc_current_stage,
            "created_by": created_by,
            "assigned_to": assigned_to,
            "is_locked": is_locked,
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
        
        # 📋 Списки для <select> в шаблоне
        "stages": [s.name for s in DocumentStage],
        "statuses": [s.value for s in DocumentStatus],
        "actions": list(ProblemAction),  # 👈 Для выпадающего списка "Действие"
    })

@router.get("/reports/problem-registrations/list")
async def problem_registrations_list_page(
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
    created_by_username: str = "",
    sort_by: str = "id",
    sort_order: str = "desc",
    page: int = 1,
    assigned_to: str = "",
    db=Depends(get_db),
):
    """Страница списка всех регистраций проблем с фильтрами и пагинацией."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    skip = (page - 1) * 50
    # 🔽 Хелпер для безопасной конвертации str → int | None
    def to_int_or_none(val: str) -> int | None:
        if not val or not val.strip():
            return None
        try:
            return int(val.strip())
        except (ValueError, TypeError):
            return None
    from app.reports.problem_registrations.pr_schemas import ProblemRegistrationFilter
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
        assigned_to=to_int_or_none(assigned_to),
    )
    result = await service.get_all(skip=skip, limit=50, filters=filters)

    total_pages = max(1, (result.total + 49) // 50)

    return templates.TemplateResponse("problem_registrations_list.html", {
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
            "created_by_username": created_by_username,
            "assigned_to": assigned_to,
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

    from app.reports.problem_registrations.pr_schemas import ProblemRegistrationCreate
    from app.reports.problem_registrations.pr_public_services import PublicProblemRegistrationService

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

@router.get("/reports/problem-registrations/locked")
async def problem_registrations_locked_list_page(
    request: Request,
    # 🔍 Фильтры
    subject: str = "",
    track_id: str = "",
    detected_from: str = "",
    detected_to: str = "",
    sort_by: str = "id",
    sort_order: str = "desc",
    page: int = 1,
    db=Depends(get_db),
):
    """Страница списка ЗАБЛОКИРОВАННЫХ регистраций проблем с автофильтром по департаменту."""
    # 🔐 Авторизация
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    skip = (page - 1) * 50

    # 🔽 Хелпер для безопасной конвертации str → int | None
    def to_int_or_none(val: str) -> int | None:
        if not val or not val.strip():
            return None
        try:
            return int(val.strip())
        except (ValueError, TypeError):
            return None

    # 🏢 Автофильтр по департаменту пользователя
    user_department_id = None
    is_admin = getattr(current_user, "is_admin", False) or getattr(current_user, "role", "") == "admin"

    if not is_admin:
        # 🔥 Правильно: department_id хранится в UserProfile, а не в User
        profile = getattr(current_user, "profile", None)
        if profile:
            user_department_id = getattr(profile, "department_id", None)
            # Если department_id может быть вложенным объектом (Pydantic), берём .id:
            # if hasattr(user_department_id, "id"):
            #     user_department_id = user_department_id.id
    from app.knowledge_base.public_services import PublicDepartmentService
    pds = PublicDepartmentService(db)
    _pds = await pds.get_by_id(user_department_id)
    # print(f"🔍 DEBUG: is_admin={is_admin}, user_department_id={user_department_id}, {_pds.name}")  # Для отладки
    department_name = _pds.name

    
    # 📦 Фильтры + принудительное is_locked=True
    from app.reports.problem_registrations.pr_schemas import ProblemRegistrationFilter
    filters = ProblemRegistrationFilter(
        subject=subject or None,
        track_id=track_id or None,
        detected_from=datetime.fromisoformat(detected_from) if detected_from else None,
        detected_to=datetime.fromisoformat(detected_to + "T23:59:59") if detected_to else None,
        # 🔒 Жёсткий фильтр: только заблокированные
        is_locked=True,
        # 🏢 Автофильтр по департаменту (только для не-админов)
        responsible_department_id=user_department_id,
        # Сортировка и пагинация
        sort_by=sort_by,
        sort_order=sort_order,
    )

    result = await service.get_all(skip=skip, limit=50, filters=filters)
    total_pages = max(1, (result.total + 49) // 50)

    # 🏢 Получаем список департаментов для отображения в шаблоне (опционально)
    from app.knowledge_base.public_services import PublicDepartmentService
    PDS = PublicDepartmentService(db)
    departments = await PDS.get_all()

    return templates.TemplateResponse(
        "problem_registrations_locked_list.html",
        {
            "request": request,
            "items": result.items,
            "total": result.total,
            "page": page,
            "department_name": department_name,
            "total_pages": total_pages,
            "current_user": current_user,
            "is_locked_view": True,
            "user_department_id": user_department_id,  # 👈 Для отображения в шаблоне
            "filters": {
                "subject": subject,
                "track_id": track_id,
                "detected_from": detected_from,
                "detected_to": detected_to,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
            "stages": [s.name for s in DocumentStage],
            "statuses": [s.value for s in DocumentStatus],
            "departments": departments.items,  # 👈 Если нужно показать в фильтре
        }
    )


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
    from app.reports.documents.document_public_service import PublicDocumentService
    doc_service = PublicDocumentService(db)
    attachments = await doc_service.get_attachments(item.document_id)

    # Получаем ID чата по документу
    from app.messages.public_services import PublicChatService
    chat_service = PublicChatService(db)
    chat_id = await chat_service.get_chat_id_by_document(item.document_id)

    from app.knowledge_base.public_services import PublicDepartmentService
    PDS = PublicDepartmentService(db)

    responsible_department_name = await PDS.get_by_id(item.responsible_department_id)

    
    return templates.TemplateResponse("view_problem_registration.html", {
        "request": request,
        "item": item,
        "current_user": current_user,
        "chat_id": chat_id,
        "attachments": attachments,
        "responsible_department_name" : responsible_department_name.name if responsible_department_name else None,
    })



@router.get("/reports/problem-registrations/owner/{registration_id}")
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
    from app.reports.documents.document_public_service import PublicDocumentService
    doc_service = PublicDocumentService(db)
    attachments = await doc_service.get_attachments(item.document_id)

    # Получаем ID чата по документу
    from app.messages.public_services import PublicChatService
    chat_service = PublicChatService(db)
    chat_id = await chat_service.get_chat_id_by_document(item.document_id)

    from app.knowledge_base.public_services import PublicDepartmentService
    PDS = PublicDepartmentService(db)

    responsible_department_name = await PDS.get_by_id(item.responsible_department_id)

    
    return templates.TemplateResponse("owner_problem_registration.html", {
        "request": request,
        "item": item,
        "current_user": current_user,
        "chat_id": chat_id,
        "attachments": attachments,
        "responsible_department_name" : responsible_department_name.name if responsible_department_name else None,
    })

@router.get("/reports/problem-registrations/{registration_id}/confirm")
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
    from app.reports.documents.document_public_service import PublicDocumentService
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

    from app.reports.problem_registrations.pr_schemas import ProblemRegistrationUpdate
    from app.reports.problem_registrations.pr_public_services import PublicProblemRegistrationService

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
            from app.reports.documents.document_public_service import PublicDocumentService
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

    from app.reports.documents.document_public_service import PublicDocumentService
    doc_service = PublicDocumentService(db)
    await doc_service.delete_attachment(attachment_id, user_id=current_user.id)

    return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}/edit", status_code=303)


@router.post("/reports/problem-registrations/{registration_id}/archive")
async def archive_problem_registration(
    request: Request,
    registration_id: int,
    db=Depends(get_db),
):
    """Архивировать регистрацию проблемы."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    await service.archive(registration_id, user_id=current_user.id)
    return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)


@router.post("/reports/problem-registrations/{registration_id}/unarchive")
async def unarchive_problem_registration(
    request: Request,
    registration_id: int,
    db=Depends(get_db),
):
    """Восстановить регистрацию проблемы из архива."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    await service.unarchive(registration_id, user_id=current_user.id)
    return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)


@router.post("/reports/problem-registrations/{registration_id}/assign")
async def assign_user_to_problem_registration(
    request: Request,
    registration_id: int,
    user_id_to_assign: int = Form(...),
    db=Depends(get_db),
):
    """Назначить пользователя на регистрацию проблемы."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result
    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    try:
        await service.assign_user(registration_id, user_id_to_assign=user_id_to_assign, current_user_id=current_user.id)
    except ValueError as e:
        # Пользователь уже участник чата — показываем ошибку
        return templates.TemplateResponse("view_problem_registration.html", {
            "request": request,
            "item": item,
            "current_user": current_user,
            "error": str(e),
        })

    return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)


@router.post("/reports/problem-registrations/{registration_id}/assign-self")
async def assign_self_to_problem_registration(
    request: Request,
    registration_id: int,
    db=Depends(get_db),
):
    """Назначить себя на регистрацию проблемы."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result
    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    await service.assign_self(registration_id, user_id=current_user.id)
    return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)


@router.post("/reports/problem-registrations/{registration_id}/delete")
async def delete_problem_registration(
    request: Request,
    registration_id: int,
    db=Depends(get_db),
):
    """Удалить регистрацию проблемы."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    await service.delete(registration_id)
    return RedirectResponse(url="/reports/problem-registrations/list", status_code=303)


@router.post("/reports/problem-registrations/{registration_id}/unassign")
async def unassign_problem_registration(
    request: Request,
    registration_id: int,
    db=Depends(get_db),
):
    """Снять назначенного пользователя"""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicProblemRegistrationService(db)
    item = await service.get_by_id(registration_id)
    if not item:
        return RedirectResponse(url="/reports/problem-registrations", status_code=303)

    try:
        await service.unassign(registration_id, current_user_id=current_user.id)
    except ValueError as e:
        # Пользователь уже участник чата — показываем ошибку
        return templates.TemplateResponse("view_problem_registration.html", {
            "request": request,
            "item": item,
            "current_user": current_user,
            "error": str(e),
        })

    return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}", status_code=303)


@router.get("/reports/problem-registrations/{registration_id}/edit-details")
async def edit_problem_registration_details_page(
    request: Request,
    registration_id: int,
    db=Depends(get_db),
):
    """Страница редактирования дополнительной информации регистрации проблемы."""
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

    # Получаем список отделов для выпадающего списка
    from app.knowledge_base.public_services import PublicDepartmentService
    department_service = PublicDepartmentService(db)
    departments = await department_service.get_all(skip=0, limit=1000)

    # Пробрасываем enum в шаблон для генерации <option>
    from app.reports.problem_registrations.pr_schemas import ProblemAction
    from app.reports.documents.document_public_service import PublicDocumentService
    # Получаем прикреплёные документы
    doc_service = PublicDocumentService(db)
    attachments = await doc_service.get_attachments(item.document_id)

    return templates.TemplateResponse("edit_problem_registration_details.html", {
        "request": request,
        "item": item,
        "attachments": attachments,
        "current_user": current_user,
        "departments": departments.items,
        "ProblemAction": ProblemAction,
        "now": datetime.now,
    })


@router.post("/reports/problem-registrations/{registration_id}/edit-details")
async def edit_problem_registration_details_post(
    request: Request,
    registration_id: int,
    approved_at: str = Form(""),
    action: str = Form(""),
    responsible_department_id: str = Form(""),
    comment: str = Form(""),
    db=Depends(get_db),
):
    """Обработка формы редактирования дополнительной информации регистрации проблемы."""
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

    # --- Парсинг данных формы ---
    parsed_approved_at = None
    if approved_at and approved_at.strip():
        try:
            parsed_approved_at = datetime.fromisoformat(approved_at.strip())
        except (ValueError, TypeError):
            pass

    parsed_dept_id = None
    if responsible_department_id and responsible_department_id.strip():
        try:
            parsed_dept_id = int(responsible_department_id.strip())
        except ValueError:
            pass

    parsed_comment = comment.strip() if comment else None

    try:
        from app.reports.problem_registrations.pr_schemas import (
            ProblemRegistration_DetaleUpdate,
            ProblemRegistrationUpdate,
        )
        
        # 🔧 FIX 1: Передаём пустую строку вместо None — валидатор подставит дефолт
        update_data = ProblemRegistration_DetaleUpdate(
            approved_at=parsed_approved_at,
            action=action.strip() if action else "",  # ← Было: else None
            responsible_department_id=parsed_dept_id,
            comment=parsed_comment,
        )

        # 1️⃣ Сохраняем детали
        await service.update_detale(registration_id, update_data)

        # 🔒 2️⃣ Блокируем регистрацию
        await service.update(registration_id, ProblemRegistrationUpdate(is_locked=True))

        return RedirectResponse(url=f"/reports/problem-registrations/{registration_id}/confirm", status_code=303)

    except Exception as e:
        # 🔧 FIX 2: Обязательно сбрасываем сессию после ошибки!
        await db.rollback()
        error_msg = str(e)

    # В случае ошибки возвращаем форму с сохранёнными данными
    from app.knowledge_base.public_services import PublicDepartmentService
    department_service = PublicDepartmentService(db)
    departments = await department_service.get_all(skip=0, limit=1000)

    # Получаем прикреплёные документы
    from app.reports.documents.document_public_service import PublicDocumentService
    doc_service = PublicDocumentService(db)
    attachments = await doc_service.get_attachments(item.document_id)

    from app.reports.problem_registrations.pr_schemas import ProblemAction

    return templates.TemplateResponse("edit_problem_registration_details.html", {
        "request": request,
        "item": item,
        "current_user": current_user,
        "departments": departments.items,
        "ProblemAction": ProblemAction,
        "attachments": attachments,
        "error": error_msg,
        "form_data": {
            "approved_at": approved_at,
            "action": action,
            "responsible_department_id": responsible_department_id,
            "comment": comment,
        },
        "now": datetime.now,
    })


