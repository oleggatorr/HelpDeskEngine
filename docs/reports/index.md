# Модуль отчетов (Reports)

## Обзор

Модуль управления документами и их расширениями:
- Отчет о несоответствии (`NonconformityReport`)
- Анализ несоответствия (`NonconformityAnalysis`)
- Корректирующее действие (`CorrectiveAction`)

## Архитектура

### Модель данных

```
┌─────────────┐
│  Document   │  ← базовый документ (id, status, doc_type, creator_id)
└──────┬──────┘
       │ 1:1
       ├──────────────────┬──────────────────┐
       ▼                  ▼                  ▼
┌─────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│Nonconformity    │ │Nonconformity     │ │Corrective        │
│Report           │ │Analysis          │ │Action            │
└─────────────────┘ └──────────────────┘ └──────────────────┘
```

### Связи

- `Document` ↔ `NonconformityReport` — **1:1** (PK-FK)
- `Document` ↔ `NonconformityAnalysis` — **1:1** (PK-FK)
- `Document` ↔ `CorrectiveAction` — **1:1** (PK-FK)

При создании расширения автоматически создается базовый `Document`.

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

Работа с базовыми документами.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `get_by_id` | `doc_id: int` | `Optional[DocumentResponse]` | Получение документа по ID |
| `get_all` | `skip, limit, фильтры` | `DocumentListResponse` | Пагинированный список |
| `update_status` | `doc_id, status` | `DocumentResponse` | Изменение статуса |
| `delete` | `doc_id` | `bool` | Удаление с каскадом |

### INonconformityReportService (`nonconformity_report_service.py`)

Создание и получение отчетов о несоответствии.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `create` | `NonconformityReportCreate` | `NonconformityReportResponse` | Создание Document + Report |
| `get_by_id` | `report_id: int` | `Optional[NonconformityReportResponse]` | Получение по ID |
| `get_by_document_id` | `doc_id: int` | `Optional[NonconformityReportResponse]` | Получение по ID документа |

### INonconformityAnalysisService (`nonconformity_analysis_service.py`)

Создание и получение анализов несоответствий.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `create` | `NonconformityAnalysisCreate` | `NonconformityAnalysisResponse` | Создание Document + Analysis |
| `get_by_id` | `analysis_id: int` | `Optional[NonconformityAnalysisResponse]` | Получение по ID |
| `get_by_document_id` | `doc_id: int` | `Optional[NonconformityAnalysisResponse]` | Получение по ID документа |

### ICorrectiveActionService (`corrective_action_service.py`)

Создание и получение корректирующих действий.

| Метод | Вход | Выход | Описание |
|-------|------|-------|----------|
| `create` | `CorrectiveActionCreate` | `CorrectiveActionResponse` | Создание Document + Action |
| `get_by_id` | `action_id: int` | `Optional[CorrectiveActionResponse]` | Получение по ID |
| `get_by_document_id` | `doc_id: int` | `Optional[CorrectiveActionResponse]` | Получение по ID документа |

## Схемы (Pydantic)

### DocumentResponse
```python
id: int
doc_type: DocType
status: DocStatus
creator_id: Optional[int]
created_at: datetime
```

### NonconformityReportResponse
```python
id: int
document: DocumentResponse
```

### NonconformityAnalysisResponse
```python
id: int
document: DocumentResponse
```

### CorrectiveActionResponse
```python
id: int
document: DocumentResponse
```

## Файлы модуля

| Файл | Описание |
|------|----------|
| `models.py` | SQLAlchemy модели |
| `schemas.py` | Pydantic схемы |
| `services/document_service.py` | Сервис базовых документов |
| `services/nonconformity_report_service.py` | Сервис отчетов о несоответствии |
| `services/nonconformity_analysis_service.py` | Сервис анализа несоответствий |
| `services/corrective_action_service.py` | Сервис корректирующих действий |
