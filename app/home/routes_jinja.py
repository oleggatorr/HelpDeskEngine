from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader, Environment
from pathlib import Path

from app.core.database import get_db
from app.auth.routes_jinja import require_auth

router = APIRouter()

local_templates = Path(__file__).parent / "templates"
global_templates = Path(__file__).parent.parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(global_templates)),
    autoescape=True,
)

templates = Jinja2Templates(env=env)


@router.get("/")
async def home_page(
    request: Request,
    db=Depends(get_db),
):
    """Домашняя страница."""
    auth_result = await require_auth(request, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    current_user = auth_result

    return templates.TemplateResponse("pages/home.html", {
        "request": request,
        "current_user": current_user,
    })
