# app/reports/correction/correction_routes_jinja.py
from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from datetime import datetime
from pathlib import Path
import uuid

from app.core.database import get_db
from app.core.templates import templates
from app.auth.routes_jinja import require_auth
from app.reports.correction.correction_public_services import PublicDocumentService
from app.reports.correction.correction_schemas import CorrectionCreate, CorrectionStatus
from app.reports.documents.document_models import DocumentLanguage, DocumentPriority, DocumentStatus as DocStatus
from app.reports.problem_registrations.pr_public_services import PublicProblemRegistrationService

from loguru import logger

router = APIRouter()


# ==========================================
# 🆕 CREATE — GET (форма)
# ==========================================
@router.get("/reports/corrections/create")
async def correction_create_page(
    request: Request,
    problem_registration_id: Optional[int] = None,  # 👈 Предзаполнение из заявки
    db=Depends(get_db),
):
    """Страница создания корректирующего действия."""
    logger.debug("GET /reports/corrections/create", pr_id=problem_registration_id)
    
    # 🔐 Авторизация
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    # 📦 Получаем список заявок для привязки (с фильтрацией, если передан pr_id)
    pr_service = PublicProblemRegistrationService(db)
    if problem_registration_id:
        # Если идём со страницы заявки — загружаем только её
        pr = await pr_service.get_by_id(problem_registration_id)
        pr_list = [pr] if pr else []
    else:
        # Иначе — список последних открытых заявок для выбора
        pr_result = await pr_service.get_all(skip=0, limit=100)
        pr_list = pr_result.items

    # 📋 Списки для <select>
    correction_statuses = [s.value for s in CorrectionStatus]
    languages = [lang.value for lang in DocumentLanguage]
    priorities = [p.value for p in DocumentPriority]

    logger.info("Correction create page loaded", user_id=current_user.id, pr_count=len(pr_list))
    
    return templates.TemplateResponse("correction_create.html.j2", {
        "request": request,
        "problem_registrations": pr_list,
        "correction_statuses": correction_statuses,
        "languages": languages,
        "priorities": priorities,
        "form_data": None,
        "error": None,
        "now": datetime.now,
        "preselected_pr_id": problem_registration_id,  # Для JS/автовыбора
        "current_user": current_user,
    })


# ==========================================
# 🆕 CREATE — POST (обработка)
# ==========================================
@router.post("/reports/corrections/create")
async def correction_create_submit(
    request: Request,
    # 🔗 Привязка к заявке
    problem_registration_id: int = Form(..., gt=0),
    
    # 📝 Основные поля Correction
    title: str = Form(..., min_length=3, max_length=200),
    description: Optional[str] = Form(None),
    corrective_action: str = Form(..., min_length=3),
    status: str = Form("planned"),
    planned_date: Optional[str] = Form(None),
    completed_date: Optional[str] = Form(None),
    
    # ⚙️ Параметры документа
    doc_language: str = Form("ru"),
    doc_priority: str = Form("medium"),
    doc_status: str = Form("open"),
    
    # 📎 Вложения
    files: List[UploadFile] = File(None),
    
    db=Depends(get_db),
):
    """Обработка создания коррекции через форму."""
    logger.info("POST /reports/corrections/create", title=title, pr_id=problem_registration_id)
    
    # 🔐 Авторизация
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    # 🔄 Хелпер для парсинга дат из datetime-local
    def parse_dt(val: Optional[str]) -> Optional[datetime]:
        if not val or not val.strip():
            return None
        try:
            # datetime-local возвращает формат "2026-05-15T10:30"
            return datetime.fromisoformat(val)
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse date", value=val, error=str(e))
            return None

    # 📦 Обработка вложений
    attachment_files = []
    upload_dir = Path("uploads/corrections")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    if files:
        for file in files:
            if file.filename and file.filename.strip():
                try:
                    # Генерируем уникальное имя файла
                    ext = Path(file.filename).suffix or ".bin"
                    unique_name = f"{uuid.uuid4().hex}{ext}"
                    file_path = upload_dir / unique_name
                    
                    # Сохраняем файл
                    with open(file_path, "wb") as f:
                        content = await file.read()
                        f.write(content)
                    

                    logger.debug("File uploaded", filename=file.filename, path=str(file_path))
                    
                except Exception as e:
                    logger.error("File upload failed", filename=file.filename, error=str(e))
                    # Не прерываем создание, если один файл не загрузился

    # 📦 Сборка схемы создания
    correction_data = CorrectionCreate(
        problem_registration_id=problem_registration_id,
        title=title,
        description=description.strip() if description else None,
        corrective_action=corrective_action,
        status=status,
        planned_date=parse_dt(planned_date),
        completed_date=parse_dt(completed_date),
        doc_language=doc_language,
        doc_priority=doc_priority,
        doc_status=doc_status,
        attachment_files=attachment_files if attachment_files else None,
    )

    # 🚀 Создание через сервис
    service = PublicCorrectionService(db)
    
    try:
        result = await service.create(correction_data, created_by=current_user.id)
        logger.info("Correction created successfully", correction_id=result.id, track_id=result.track_id)
        
        # ✅ Успех — редирект на страницу созданной коррекции
        return RedirectResponse(
            url=f"/reports/corrections/{result.id}",
            status_code=303,  # See Other — предотвращает повторную отправку формы
            headers={"Cache-Control": "no-cache"}
        )
        
    except HTTPException as e:
        logger.warning("Correction creation failed", error=e.detail, status=e.status_code)
        error_msg = e.detail
        
    except ValueError as e:
        logger.warning("Validation error during correction creation", error=str(e))
        error_msg = str(e)
        
    except Exception as e:
        logger.error("Unexpected error during correction creation", error=str(e), exc_info=True)
        error_msg = "Внутренняя ошибка сервера при создании коррекции"

    # ❌ Ошибка — возвращаем форму с данными и сообщением об ошибке
    logger.debug("Re-rendering form with error", error=error_msg)
    
    # Восстанавливаем списки для <select>
    pr_service = PublicProblemRegistrationService(db)
    pr_result = await pr_service.get_all(skip=0, limit=100)
    
    return templates.TemplateResponse("correction_create.html.j2", {
        "request": request,
        "problem_registrations": pr_result.items,
        "correction_statuses": [s.value for s in CorrectionStatus],
        "languages": [lang.value for lang in DocumentLanguage],
        "priorities": [p.value for p in DocumentPriority],
        "form_data": correction_data,  # Сохраняем введённые пользователем данные
        "error": error_msg,
        "now": datetime.now,
        "preselected_pr_id": problem_registration_id,
        "current_user": current_user,
    })


# ==========================================
# 👁️ READ — DETAIL PAGE (Jinja)
# ==========================================
@router.get("/reports/corrections/{correction_id}")
async def correction_detail_page(
    request: Request,
    correction_id: int,
    db=Depends(get_db),
):
    """Страница просмотра деталей коррекции."""
    logger.debug("GET /reports/corrections/{correction_id}", correction_id=correction_id)
    
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicCorrectionService(db)
    correction = await service.get_by_id(correction_id)
    
    if not correction:
        logger.warning("Correction not found for detail page", correction_id=correction_id)
        raise HTTPException(status_code=404, detail="Коррекция не найдена")

    # 📦 Получаем связанные данные для отображения
    pr_service = PublicProblemRegistrationService(db)
    problem_registration = await pr_service.get_by_id(correction.problem_registration_id)

    logger.info("Correction detail page loaded", correction_id=correction_id, track_id=correction.track_id)
    
    return templates.TemplateResponse("correction_detail.html.j2", {
        "request": request,
        "correction": correction,
        "problem_registration": problem_registration,
        "current_user": current_user,
        "can_edit": not correction.is_locked and correction.created_by == current_user.id,
        "can_confirm": not correction.is_locked,  # Бизнес-правило: подтверждать может автор/админ
    })