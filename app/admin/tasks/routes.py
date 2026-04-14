from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin, oauth2_scheme
from app.admin.tasks.services import AdminTaskService

router = APIRouter(
    prefix="/admin/tasks",
    tags=["Admin — Tasks"],
    dependencies=[Depends(oauth2_scheme)],
)


def _get_service(db: AsyncSession = Depends(get_db)) -> AdminTaskService:
    return AdminTaskService(db)


@router.get("/", summary="Список задач")
async def list_tasks(
    _admin=Depends(require_admin),
    svc: AdminTaskService = Depends(_get_service),
):
    """Получить список всех задач (TODO)."""
    return {"status": "not_implemented"}
