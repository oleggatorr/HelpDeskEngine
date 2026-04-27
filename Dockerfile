FROM python:3.12-slim

# Создаём пользователя для безопасности
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Копируем зависимости отдельно для кэширования слоёв
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем весь проект
COPY . .

# Права и пользователь
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Запуск: Uvicorn с воркерами для продакшена
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]