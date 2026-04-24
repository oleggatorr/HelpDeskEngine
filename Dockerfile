FROM python:3.12-slim

# Безопасность: не запускать от root
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Копируем зависимости отдельно для кэширования слоёв
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Меняем права и пользователя
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Production-запуск (Uvicorn 0.23+ поддерживает --workers)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]