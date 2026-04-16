from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse

# from fastapi.templating import Jinja2Templates
# from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from app.core.templates import templates

from pathlib import Path
from datetime import datetime

from app.core.database import get_db
from app.auth.routes_jinja import require_auth
from app.reports.documents.public_services.document import PublicDocumentService
from app.reports.enums import DocumentStage

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


@router.get("/reports/documents")
async def documents_page(
    request: Request,
    track_id: str = "",
    status: str = "",
    doc_type_id: int = 0,
    current_stage: str = "",
    created_from: str = "",
    created_to: str = "",
    sort_by: str = "id",
    sort_order: str = "desc",
    page: int = 1,
    db=Depends(get_db),
):
    """Страница списка документов с фильтрами и сортировкой."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    service = PublicDocumentService(db)
    skip = (page - 1) * 50

    result = await service.list_filtered(
        skip=skip, limit=50,
        track_id=track_id or None,
        status=status or None,
        doc_type_id=doc_type_id or None,
        current_stage=DocumentStage[current_stage] if current_stage else None,
        created_from=datetime.fromisoformat(created_from) if created_from else None,
        created_to=datetime.fromisoformat(created_to + "T23:59:59") if created_to else None,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total_pages = max(1, (result.total + 49) // 50)

    return templates.TemplateResponse("documents.html", {
        "request": request,
        "documents": result.documents,
        "total": result.total,
        "page": page,
        "total_pages": total_pages,
        "current_user": current_user,
        "filters": {
            "track_id": track_id,
            "status": status,
            "doc_type_id": doc_type_id,
            "current_stage": current_stage,
            "created_from": created_from,
            "created_to": created_to,
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
        "stages": [s.name for s in DocumentStage],
    })
