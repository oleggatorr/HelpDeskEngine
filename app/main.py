from fastapi import FastAPI
from apps.auth.routes import router as auth_router
from apps.reports.routes import router as reports_router
from apps.messeges.routes import router as messeges_router
from apps.tasks.routes import router as tasks_router
from apps.admin.routes import router as admin_router
from apps.knowledge_base.routes import router as knowledge_base_router

app = FastAPI(title="Help Desk Engine", version="0.1.0")

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(reports_router, prefix="/reports", tags=["Reports"])
app.include_router(messeges_router, prefix="/messeges", tags=["Messages"])
app.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(knowledge_base_router, prefix="/knowledge-base", tags=["Knowledge Base"])


@app.get("/")
def root():
    return {"status": "ok", "service": "Help Desk Engine"}
