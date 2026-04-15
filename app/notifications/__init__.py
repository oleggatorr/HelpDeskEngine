from fastapi import APIRouter

from app.notifications.routes import router as notifications_router
from app.notifications.routes_jinja import router as notifications_jinja_router


def include_notification_routers(app: APIRouter):
    """Регистрирует все роутеры приложения уведомлений."""
    # Jinja-страницы
    app.include_router(notifications_jinja_router, prefix="/notifications", tags=["Notifications — Pages"])

    # API-роуты
    app.include_router(notifications_router, prefix="/api/notifications", tags=["Notifications"])
