from sqlalchemy.ext.asyncio import AsyncSession


class AdminTaskService:
    """Сервис админки для задач/тикетов."""

    def __init__(self, db: AsyncSession):
        self.db = db
