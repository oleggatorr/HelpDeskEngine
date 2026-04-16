# app/core/templates.py
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from pathlib import Path
from app.auth.models import UserRole

from app.auth.permission_service import PermissionService

BASE_DIR = Path(__file__).parent.parent

# 📂 Список всех папок с шаблонами (порядок важен: первый найденный файл wins)
TEMPLATE_PATHS = [
    BASE_DIR / "templates",                          # Глобальные (partials, base.html)
    BASE_DIR / "auth" / "templates",                 # Auth
    BASE_DIR / "home" / "templates",                 # Home
    BASE_DIR / "messeges" / "templates",             # Messages
    BASE_DIR / "reports" / "documents" / "templates",# Documents
    BASE_DIR / "reports" / "problem_registrations" / "templates", # Problems
    # Добавьте сюда другие, если появятся:
    # BASE_DIR / "admin" / "templates",
    # BASE_DIR / "knowledge_base" / "templates",
]

# Фильтруем несуществующие папки, чтобы не было ошибок при старте
EXISTING_LOADERS = [
    FileSystemLoader(str(p)) for p in TEMPLATE_PATHS if p.is_dir()
]

# 🔧 Создаём единое окружение
env = Environment(
    loader=ChoiceLoader(EXISTING_LOADERS),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

# 🔐 Функции проверки прав для шаблонов
def user_has_role(user, role_value: str) -> bool:
    """Глобальная функция для шаблонов: проверка конкретной роли."""
    try:
        role_enum = UserRole(role_value)
        return PermissionService.has_role(user, role_enum)
    except ValueError:
        return False  # Неверное имя роли

def user_has_any_role(user, *role_values: str) -> bool:
    """Глобальная функция для шаблонов: проверка одной из ролей."""
    try:
        roles = [UserRole(v) for v in role_values]
        return PermissionService.has_any_role(user, roles)
    except ValueError:
        return False

def user_has_permission(user, permission: str) -> bool:
    """Пользователь имеет конкретное право."""
    if not user or not getattr(user, 'profile', None) or not user.profile.permissions:
        return False
    perms = user.profile.permissions.split(",") if user.profile.permissions else []
    return permission in perms or "*" in perms

# 🌍 Добавляем функции и константы в глобальную область Jinja2
env.globals.update({
    "user_has_role": user_has_role,
    "user_has_any_role": user_has_any_role,
    "user_has_permission": user_has_permission,
    "UserRole": UserRole,
})

# 📤 Экспортируем готовый объект
templates = Jinja2Templates(env=env)