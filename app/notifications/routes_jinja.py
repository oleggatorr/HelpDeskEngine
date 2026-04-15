from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def notifications_page(request: Request):
    """Страница уведомлений."""
    return templates.TemplateResponse("notifications/notifications.html", {"request": request})
