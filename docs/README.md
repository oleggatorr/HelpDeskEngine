# Шаблоны (Templates)

## Структура

```
app/templates/
├── base.html              # Базовый шаблон (собирает header + body + footer)
└── partials/
    ├── header.html        # Шапка: DOCTYPE, <head>, Bootstrap CSS, открытие <body>
    ├── body.html          # Тело: блок контента
    ├── footer.html        # Футер: copyright, Bootstrap JS, закрытие тегов
    ├── list.html          # Макрос render_list — список с карточкой
    ├── list_item.html     # Макрос render_list_item — один элемент списка
    └── document_canvas.html  # Белый холст документа с полями форм
```

## Подключение в роутах

```python
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/page")
async def page(request: Request):
    return templates.TemplateResponse("base.html", {
        "request": request,
        "title": "Моя страница",
        "items": [{"name": "Задача 1", "status": "Новая"}, ...],
    })
```

## base.html

Базовый шаблон собирает все части вместе:

```jinja
{% include "partials/header.html" %}
{% include "partials/body.html" %}
{% include "partials/footer.html" %}
```

Переопределение блоков в дочерних шаблонах:

```jinja
{% extends "base.html" %}

{% block title %}Моя страница{% endblock %}

{% block head %}
<style> .custom { color: red; } </style>
{% endblock %}

{% block content %}
<h1>Привет!</h1>
{% endblock %}

{% block scripts %}
<script> console.log("loaded"); </script>
{% endblock %}
```

## list.html — render_list

### Простой список

```jinja
{% from "partials/list.html" import render_list %}

{{ render_list(
    items=tasks,
    item_key="title",
    title="Список задач"
) }}
```

### Список со ссылками

```jinja
{{ render_list(
    items=tasks,
    item_key="title",
    item_url=lambda t: "/tasks/" ~ t.id,
    title="Задачи"
) }}
```

### Список с бейджами

```jinja
{{ render_list(
    items=tasks,
    item_key="title",
    item_url=lambda t: "/tasks/" ~ t.id,
    badge_key="status",
    title="Задачи"
) }}
```

### Параметры макроса

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `items` | list | — | Список элементов |
| `item_key` | str | `"name"` | Ключ для отображения текста (если item — dict) |
| `item_url` | callable | `None` | Функция генерации URL для элемента |
| `badge_key` | str | `None` | Ключ для бейджа (если есть — отображается) |
| `empty_text` | str | `"Список пуст"` | Текст при пустом списке |
| `title` | str | `None` | Заголовок карточки |
| `bordered` | bool | `True` | Рамка карточки |
| `flush` | bool | `False` | Убрать границы элементов |
| `hover` | bool | `True` | Подсветка при наведении |

## list_item.html — render_list_item

```jinja
{% from "partials/list_item.html" import render_list_item %}

{{ render_list_item(
    item="Задача #1",
    index=1,
    url="/tasks/1",
    badge="Новая",
    badge_class="bg-success"
) }}
```

### Параметры макроса

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `item` | str | — | Текст элемента |
| `index` | int | `None` | Номер (бейдж слева) |
| `url` | str | `None` | Ссылка на элемент |
| `badge` | str | `None` | Текст бейджа |
| `badge_class` | str | `"bg-primary"` | CSS-класс бейджа |

## Полный пример страницы

```jinja
{% extends "base.html" %}

{% block title %}Задачи — Help Desk{% endblock %}

{% block content %}
<div class="container mt-4">
    <h1>Задачи</h1>

    {% from "partials/list.html" import render_list %}
    {{ render_list(
        items=tasks,
        item_key="title",
        item_url=lambda t: "/tasks/" ~ t.id,
        badge_key="status",
        title="Список задач",
        empty_text="Задач пока нет"
    ) }}
</div>
{% endblock %}
```

## document_canvas.html — Холст документа

Белый холст с тенью для расположения форм документа.

### Простой документ

```jinja
{% extends "base.html" %}

{% block content %}
<div class="container mt-4">
    {% from "partials/document_canvas.html" import render_document_canvas %}
    {% call render_document_canvas(
        title="Регистрация проблемы",
        subtitle="Заполните информацию о выявленной проблеме",
        doc_number="PRB-001",
        doc_date="2026-04-09"
    ) %}
        <p>Содержимое документа...</p>
    {% endcall %}
</div>
{% endblock %}
```

### Документ с формой

```jinja
{% extends "base.html" %}

{% block content %}
<div class="container mt-4">
    {% from "partials/document_canvas.html" import render_document_canvas, render_field, render_textarea, render_select, render_field_row %}

    <form method="post">
        {% call render_document_canvas(
            title="Регистрация проблемы",
            doc_number=doc.number,
            doc_date=doc.created_at,
            actions=[
                {"label": "Сохранить", "style": "primary"},
                {"label": "Отмена", "url": "/documents", "style": "secondary"}
            ]
        ) %}
            {{ render_field("Номер документа", "number", value=doc.number, required=True) }}
            {{ render_field("Место обнаружения", "location_id", type="number", required=True) }}
            {{ render_textarea("Описание проблемы", "description", required=True, rows=5) }}
            {{ render_select("Статус", "status_id", [(1, "Новый"), (2, "В работе")], selected=1) }}
        {% endcall %}
    </form>
</div>
{% endblock %}
```

### Макросы document_canvas.html

| Макрос | Описание |
|--------|----------|
| `render_document_canvas` | Белый холст документа с шапкой, телом и действиями |
| `render_field` | Поле ввода (input) |
| `render_textarea` | Многострочное текстовое поле |
| `render_select` | Выпадающий список |
| `render_field_row` | Два поля в одну строку (col-md-6) |

### render_document_canvas — параметры

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `title` | str | `None` | Заголовок документа |
| `subtitle` | str | `None` | Подзаголовок |
| `doc_number` | str | `None` | Номер документа |
| `doc_date` | str | `None` | Дата документа |
| `actions` | list | `None` | Кнопки действий: `[{"label": "...", "url": "...", "style": "primary"}]` |

### render_field — параметры

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `label` | str | — | Метка поля |
| `name` | str | — | Имя поля (name, id) |
| `value` | str | `None` | Значение |
| `type` | str | `"text"` | Тип input |
| `required` | bool | `False` | Обязательное поле |
| `placeholder` | str | `None` | Подсказка |
| `help_text` | str | `None` | Текст помощи |
| `readonly` | bool | `False` | Только для чтения |

### render_select — параметры

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `label` | str | — | Метка |
| `name` | str | — | Имя поля |
| `options` | list | — | `[(value, label), ...]` |
| `selected` | any | `None` | Выбранное значение |
| `required` | bool | `False` | Обязательное |
| `help_text` | str | `None` | Текст помощи |
