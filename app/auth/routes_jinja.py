from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from pathlib import Path
from urllib.parse import urlencode
from jose import jwt, JWTError

from app.core.database import get_db
from app.core.config import settings
from app.auth.public_services import PublicAuthService, PublicUserService
from app.auth.models import User

router = APIRouter()

# Локальные шаблоны модуля + общие из app/templates
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


async def get_current_user_from_cookie(request: Request, db=Depends(get_db)) -> User | None:
    """Получение пользователя из cookie (не вызывает ошибку, если не авторизован)."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        return None

    service = PublicUserService(db)
    return await service.get_by_id(user_id)


async def require_auth(request: Request, db) -> User | RedirectResponse:
    """Проверяет авторизацию. Возвращает User или RedirectResponse на логин."""
    user = await get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login-page", status_code=303)
    return user


@router.get("/login-page")
async def login_page(request: Request, error: str = ""):
    """Страница входа (Jinja2)."""
    # Если уже авторизован — редирект на главную
    user = await get_current_user_from_cookie(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
    })


@router.post("/login-page")
async def login_page_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db),
):
    """Обработка формы входа."""
    service = PublicAuthService(db)
    try:
        from app.auth.schemas import LoginRequest
        result = await service.login(LoginRequest(login=username, password=password))
        # Сохраняем токены в cookies (чистый токен, без "Bearer ")
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            samesite="lax",
            max_age=30 * 60,  # 30 минут
        )
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            samesite="lax",
            max_age=7 * 24 * 60 * 60,  # 7 дней
        )
        return response
    except Exception:
        query = urlencode({"error": "Неверный логин или пароль"})
        return RedirectResponse(url=f"/auth/login-page?{query}", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    """Выход — удаление cookies."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return response


@router.get("/register-page")
async def register_page(request: Request):
    """Страница регистрации (Jinja2)."""
    return templates.TemplateResponse("register.html", {"request": request})
