from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter()


@router.get("/")
async def get_notifications(db: Session = Depends(get_db)):
    """Получить все уведомления текущего пользователя."""
    return {"message": "Get notifications"}
