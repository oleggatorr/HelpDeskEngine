# Document
## Модель

> **База данных:** PostgreSQL / MySQL  
> **ORM:** SQLAlchemy 2.x  
> **Фреймворк:** FastAPI  
> **Дата обновления:** 24.04.2026

---

### 🔢 Перечисления (Enums)

| Константа | Значение (Python) | Тип в БД | Описание |
|:---:|:---|:---|:---|
| `DocumentStage.NEW` | `1` | `INTEGER` | Документ создан, ожидает обработки |
| `DocumentStage.IN_PROGRESS` | `2` | `INTEGER` | В работе |
| `DocumentStage.WAITING` | `3` | `INTEGER` | Ожидание (внешние данные, согласование и т.д.) |
| `DocumentStage.CLOSED` | `4` | `INTEGER` | Закрыт |
| `DocumentLanguage.RU` | `"ru"` | `VARCHAR` | Русский язык |
| `DocumentLanguage.EN` | `"en"` | `VARCHAR` | Английский язык |
| `DocumentLanguage.CH` | `"ch"` | `VARCHAR` | Китайский язык |
| `DocumentPriority.LOW` | `"low"` | `VARCHAR` | Низкий приоритет |
| `DocumentPriority.MEDIUM` | `"medium"` | `VARCHAR` | Средний приоритет |
| `DocumentPriority.HIGH` | `"high"` | `VARCHAR` | Высокий приоритет |
| `DocumentPriority.URGENT` | `"urgent"` | `VARCHAR` | Срочный |
| `DocumentStatus.OPEN` | `"open"` | `VARCHAR` | Открыт |
| `DocumentStatus.IN_PROGRESS` | `"in_progress"` | `VARCHAR` | В обработке |
| `DocumentStatus.WAITING` | `"waiting"` | `VARCHAR` | На ожидании |
| `DocumentStatus.CLOSED` | `"closed"` | `VARCHAR` | Закрыт |
| `DocumentStatus.REJECTED` | `"rejected"` | `VARCHAR` | Отклонён |

---

### 🗃️ Таблицы и поля

#### 1. `document_types` (Справочник типов документов)

|№| Поле | Тип | Описание |
|:---:|:---|:---|:---|
| 1 | `id` | `INT` / `int` | Первичный ключ, автоинкремент, индексирован |
| 2 | `name` | `VARCHAR(100)` / `str` | Человеко-читаемое название типа. `UNIQUE`, `NOT NULL` |
| 3 | `code` | `VARCHAR(20)` / `str` | Уникальный код типа для бизнес-логики. `UNIQUE`, `NOT NULL` |

---

#### 2. `documents` (Основная сущность)

|№| Поле | Тип | Описание |
|:---:|:---|:---|:---|
| 1 | `id` | `INT` / `int` | Первичный ключ, автоинкремент, индексирован |
| 2 | `track_id` | `VARCHAR(12)` / `str` | Уникальный трекинг-номер. `UNIQUE`, `NOT NULL`, индексирован |
| 3 | `created_at` | `TIMESTAMP WITH TIME ZONE` / `datetime` | Время создания. `DEFAULT: NOW()` (на стороне БД) |
| 4 | `created_by` | `INT` / `int` | FK → `users.id`. `NULL` при удалении автора. Допускает `NULL` |
| 5 | `status` | `ENUM` / `str` | Статус документа. `DEFAULT: 'open'` |
| 6 | `doc_type_id` | `INT` / `int` | FK → `document_types.id`. `NULL` при удалении типа. Допускает `NULL` |
| 7 | `current_stage` | `ENUM` / `int` | Этап жизненного цикла. `NOT NULL`, `DEFAULT: 1 (NEW)` |
| 8 | `is_locked` | `BOOLEAN` / `bool` | Флаг блокировки редактирования. `NOT NULL`, `DEFAULT: FALSE` |
| 9 | `is_archived` | `BOOLEAN` / `bool` | Флаг архивации. `NOT NULL`, `DEFAULT: FALSE` |
| 10 | `is_anonymized` | `BOOLEAN` / `bool` | Флаг маскирования персональных данных. `NOT NULL`, `DEFAULT: FALSE` |
| 11 | `language` | `ENUM` / `str` | Язык документа. `DEFAULT: 'ru'` |
| 12 | `priority` | `ENUM` / `str` | Приоритет обработки. `DEFAULT: 'medium'` |
| 13 | `assigned_to` | `INT` / `int` | FK → `users.id`. Исполнитель. `NULL` при удалении пользователя. Допускает `NULL` |

---

#### 3. `document_attachments` (Вложения)

|№| Поле | Тип | Описание |
|:---:|:---|:---|:---|
| 1 | `id` | `INT` / `int` | Первичный ключ, автоинкремент, индексирован |
| 2 | `document_id` | `INT` / `int` | FK → `documents.id`. `NOT NULL`. `ON DELETE: CASCADE` |
| 3 | `file_path` | `VARCHAR(255)` / `str` | Путь к файлу в хранилище. `NOT NULL` |
| 4 | `original_filename` | `VARCHAR(255)` / `str` | Исходное имя файла. Допускает `NULL` |
| 5 | `file_type` | `VARCHAR(255)` / `str` | MIME-тип или расширение (напр. `application/pdf`) |
| 6 | `uploaded_by` | `INT` / `int` | FK → `users.id`. Загрузивший пользователь. `NULL` при удалении. Допускает `NULL` |
| 7 | `uploaded_at` | `TIMESTAMP WITH TIME ZONE` / `datetime` | Время загрузки. `DEFAULT: NOW()` |
| 8 | `is_deleted` | `BOOLEAN` / `bool` | Soft-delete флаг. `NOT NULL`, `DEFAULT: FALSE` |

---

#### 4. `document_logs` (Журнал аудита)

|№| Поле | Тип | Описание |
|:---:|:---|:---|:---|
| 1 | `id` | `INT` / `int` | Первичный ключ, автоинкремент, индексирован |
| 2 | `document_id` | `INT` / `int` | FK → `documents.id`. `NOT NULL`. `ON DELETE: CASCADE` |
| 3 | `user_id` | `INT` / `int` | FK → `users.id`. Кто выполнил действие. `NULL` при удалении. Допускает `NULL` |
| 4 | `action` | `VARCHAR(20)` / `str` | Код действия (напр. `CREATE`, `STATUS_CHANGE`, `FILE_UPLOAD`). `NOT NULL` |
| 5 | `field_name` | `VARCHAR(50)` / `str` | Название изменённого поля |
| 6 | `old_value` | `TEXT` / `str` | Значение до изменения |
| 7 | `new_value` | `TEXT` / `str` | Значение после изменения |
| 8 | `created_at` | `TIMESTAMP WITH TIME ZONE` / `datetime` | Временная метка лога. `DEFAULT: NOW()` |

---

### 🔗 Связи и каскады

| Источник | Цель | Тип связи | `ON DELETE` | Примечание |
|:---|:---|:---:|:---|:---|
| `Document.created_by` | `users.id` | M:1 | `SET NULL` | Сохраняет документ при удалении автора |
| `Document.assigned_to` | `users.id` | M:1 | `SET NULL` | Снимает назначение при удалении исполнителя |
| `Document.doc_type_id` | `document_types.id` | M:1 | `SET NULL` | Тип сбрасывается, документ остаётся |
| `DocumentAttachment.document_id` | `documents.id` | M:1 | `CASCADE` | Вложения удаляются вместе с документом |
| `DocumentLog.document_id` | `documents.id` | M:1 | `CASCADE` | Логи удаляются вместе с документом |

> 💡 `attachments` и `logs` в модели `Document` используют `cascade="all, delete-orphan"`, что гарантирует автоматическую очистку в SQLAlchemy при удалении родительской сущности.

## 📦 Pydantic Схемы (FastAPI API Contract)

> **Версия:** Pydantic v2  
> **Назначение:** Валидация входящих запросов, сериализация ответов, фильтрация и пагинация  
> **Файл:** `app/reports/schemas.py` (или аналогичный путь)

---

### 📋 Обзор схем

| Схема | Назначение | Метод/Контент |
|:---|:---|:---|
| `DocumentBase` | Базовая модель с общими полями и валидаторами | Наследуется `DocumentCreate` |
| `DocumentCreate` | Создание документа | `POST /documents` (`application/json`) |
| `DocumentUpdate` | Частичное обновление | `PATCH /documents/{id}` (`application/json`) |
| `DocumentResponse` | Формат ответа от сервера | `GET /documents/{id}`, `GET /documents` |
| `DocumentListResponse` | Списковый ответ с метаданными | `GET /documents` (пагинация) |
| `DocumentFilter` | Query-параметры поиска и сортировки | `GET /documents?status=open&sort_by=id` |

---

### 🔍 Поля, типы и правила валидации

#### `DocumentCreate` (POST Body)
| Поле | Тип | По умолчанию | Валидация / Примечание |
|:---|:---|:---|:---|
| `track_id` | `str \| None` | `None` | Формат: `^[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{4}$`. Если `None`, генерируется на уровне сервиса |
| `status` | `DocumentStatus` | `OPEN` | Принимает строку (`"open"`) или Enum. Валидируется автоматически |
| `doc_type_id` | `int \| None` | `None` | Должен ссылаться на существующий тип в БД |
| `current_stage` | `DocumentStage` | `NEW` | Автоматически парсит строку в Enum (`"in_progress"` → `DocumentStage.IN_PROGRESS`) |
| `is_locked` | `bool` | `False` | Флаг блокировки |
| `is_archived` | `bool` | `False` | Флаг архивации |
| `is_anonymized` | `bool` | `False` | Флаг анонимизации |
| `language` | `DocumentLanguage` | `RU` | Принимает `"ru"`, `"en"`, `"ch"` |
| `priority` | `DocumentPriority` | `MEDIUM` | Принимает `"low"`, `"medium"`, `"high"`, `"urgent"` |
| `assigned_to` | `int \| None` | `None` | ID пользователя-исполнителя |
| `created_by` | `int \| None` | `0` | ⚠️ **Рекомендуется заменить на `None` и внедрять через `Depends(get_current_user)`** |
| `attachment_files` | `list[dict] \| None` | `None` | Метаданные вложений: `[{"file_path": "...", "file_type": "..."}]` |

#### `DocumentUpdate` (PATCH Body)
| Поле | Тип | По умолчанию | Примечание |
|:---|:---|:---|:---|
| `status` | `DocumentStatus \| None` | `None` | Обновляется только при явной передаче |
| `doc_type_id` | `int \| None` | `None` |  |
| `current_stage` | `DocumentStage \| None` | `None` |  |
| `is_locked` | `bool \| None` | `False` | ⚠️ **Антипаттерн для PATCH**: `False` не отличимо от отсутствия поля. Рекомендуется `None` |
| `is_archived` | `bool \| None` | `False` |  |
| `is_anonymized` | `bool \| None` | `False` |  |
| `language` | `DocumentLanguage \| None` | `None` |  |
| `priority` | `DocumentPriority \| None` | `None` |  |
| `assigned_to` | `int \| None` | `None` |  |

#### `DocumentFilter` (Query Parameters)
| Поле | Тип | По умолчанию | Описание |
|:---|:---|:---|:---|
| `track_id` | `str \| None` | `None` | Точное совпадение |
| `created_by` | `int \| None` | `None` | Фильтр по создателю |
| `assigned_to` | `int \| None` | `None` | Фильтр по исполнителю |
| `status` | `DocumentStatus \| None` | `None` |  |
| `doc_type_id` | `int \| None` | `None` |  |
| `current_stage` | `DocumentStage \| None` | `None` |  |
| `is_locked` | `bool \| None` | `False` |  |
| `is_archived` | `bool \| None` | `False` |  |
| `is_anonymized` | `bool \| None` | `False` |  |
| `language` | `DocumentLanguage \| None` | `None` |  |
| `priority` | `DocumentPriority \| None` | `None` |  |
| `created_from` | `datetime \| None` | `None` | Диапазон `>=` |
| `created_to` | `datetime \| None` | `None` | Диапазон `<=` |
| `sort_by` | `str \| None` | `"id"` | Допустимые: `id, track_id, created_at, created_by, current_stage, priority, language` |
| `sort_order` | `str \| None` | `"desc"` | `asc` или `desc` (case-insensitive) |

#### `DocumentResponse` (Output)
- Все `Enum` поля автоматически сериализуются в строковые имена (`"OPEN"`, `"NEW"`, `"ru"`, `"medium"`).
- `current_stage` преобразуется в `.name` для читаемости.
- Использует `model_config = {"from_attributes": True}` для работы с SQLAlchemy ORM.
