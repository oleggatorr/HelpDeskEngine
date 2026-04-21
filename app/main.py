from fastapi import FastAPI
from app.home.routes_jinja import router as home_router
from app.auth.routes import router as auth_router
from app.auth.routes_jinja import router as auth_jinja_router
from app.reports.documents.document_routes import router as reports_router
from app.reports.problem_registrations.pr_routes import router as problem_registration_router
from app.reports.documents.document_routes_jinja import router as reports_jinja_router
from app.reports.problem_registrations.pr_routes_jinja import router as problem_registration_jinja_router
from app.reports.correction.routes import router as correction_router
from app.messages.routes import router as messeges_router
from app.messages.routes_jinja import router as messeges_jinja_router
from app.tasks.routes import router as tasks_router
from app.admin.users.routes import router as admin_users_router
from app.admin.messages.routes import router as admin_messages_router
from app.admin.tasks.routes import router as admin_tasks_router
from app.admin.knowledge_base.routes import router as admin_kb_router
from app.admin.reports.document_routes import router as admin_documents_router
from app.knowledge_base.routes import router as knowledge_base_router
from app.notifications import include_notification_routers

app = FastAPI(
    title="Help Desk Engine",
    version="0.1.0",
    swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": False,
    },
)

# Jinja-страницы (без префикса)
app.include_router(home_router, tags=["Home"])
app.include_router(auth_jinja_router, prefix="/auth", tags=["Auth — Pages"])
app.include_router(messeges_jinja_router, tags=["Messages — Pages"])

# API-роуты (префикс /api)
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(reports_router, prefix="/api/reports", tags=["Documents"])
app.include_router(problem_registration_router, prefix="/api/reports", tags=["Problem Registrations"])
app.include_router(reports_jinja_router, tags=["Reports — Pages"])
app.include_router(problem_registration_jinja_router, tags=["Problem Registrations — Pages"])
app.include_router(correction_router, prefix="/api/reports", tags=["Corrections"]) 
app.include_router(messeges_router, prefix="/api/messeges", tags=["Messages"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(admin_users_router, prefix="/api/admin", tags=["Admin — Users"])
app.include_router(admin_messages_router, prefix="/api/admin", tags=["Admin — Messages"])
app.include_router(admin_tasks_router, prefix="/api/admin", tags=["Admin — Tasks"])
app.include_router(admin_kb_router, prefix="/api/admin", tags=["Admin — Knowledge Base"])
app.include_router(admin_documents_router, prefix="/api/admin", tags=["Admin — Documents"])
app.include_router(knowledge_base_router, prefix="/api/knowledge-base", tags=["Knowledge Base"])

# Уведомления
include_notification_routers(app)
