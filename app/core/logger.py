import sys
import logging
from loguru import logger

def setup_logger(log_level: str = "DEBUG", log_file: str = "logs/app.log"):
    """Настройка Loguru для FastAPI"""
    
    # Убираем стандартный обработчик, чтобы не дублировать логи
    logger.remove()
    
    # Консольный вывод с цветом и форматом
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>",
        colorize=True,
        backtrace=True,  # Показывать переменные при исключениях
        diagnose=True,   # Подробный вывод ошибок
    )
    
    # Запись в файл с ротацией (10 МБ, хранить 7 дней)
    logger.add(
        log_file,
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        encoding="utf-8",
    )
    
    # Интеграция со стандартным logging (для Uvicorn/Starlette)
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            logger.opt(depth=2, exception=record.exc_info).log(level, record.getMessage())
    
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ["uvicorn", "uvicorn.access", "fastapi"]:
        logging.getLogger(name).handlers = [InterceptHandler()]
    
    return logger