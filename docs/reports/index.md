# Модуль отчетов (Reports)

## Обзор

Модуль управления базовыми документами.

## Модель данных

### Document

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `created_at` | DateTime | Время создания |
| `status` | String(255) | Статус документа |
| `doc_type` | String(20) | Тип документа |
| `creator_id` | Integer (FK) | Ссылка на `users.id` |

## Типы документов

| Тип | Значение | Описание |
|-----|----------|----------|
| `NC_REPORT` | Отчет о несоответствии | Фиксация выявленного несоответствия |
| `NC_ANALYSIS` | Анализ несоответствия | Анализ причин и оценка влияния |
| `CORRECTIVE_ACTION` | Корректирующее действие | План действий по устранению |

## Статусы документов

| Статус | Значение | Описание |
|--------|----------|----------|
| `DRAFT` | Черновик | Документ в процессе создания |
| `IN_REVIEW` | На проверке | Ожидает согласования |
| `APPROVED` | Утвержден | Документ согласован |
| `REJECTED` | Отклонен | Документ отклонен |
| `CLOSED` | Закрыт | Документ закрыт |

## Сервисы

### IDocumentService (`document_service.py`)

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `get_by_id` | `doc_id: int` | `Optional[DocumentResponse]` | Получение документа по ID |
| `get_all` | `skip, limit, фильтры` | `DocumentListResponse` | Пагинированный список |
| `update_status` | `doc_id, status` | `DocumentResponse` | Изменение статуса |
| `delete` | `doc_id` | `bool` | Удаление документа |

## Схемы (Pydantic)

### DocumentResponse
```python
id: int
doc_type: DocType
status: DocStatus
creator_id: Optional[int]
created_at: datetime
```

## Файлы модуля

| Файл | Описание |
|------|----------|
| `models.py` | SQLAlchemy модели |
| `schemas.py` | Pydantic схемы |
| `services/document_service.py` | Сервис документов |
