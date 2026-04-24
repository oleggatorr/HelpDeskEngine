from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # ✅ Сохраняем изменения после успешного выполнения
            logger.debug("✅ Transaction committed")
        except Exception as e:
            await session.rollback()  # 🔄 Откатываем при любой ошибке
            logger.error(f"❌ Transaction rolled back: {e}")
            raise
        finally:
            await session.close()  # 🔒 Закрываем сессию