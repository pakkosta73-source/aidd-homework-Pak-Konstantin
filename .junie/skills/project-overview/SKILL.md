# Investing Demo — Project Overview

**Trigger:** Use this skill when working with the Investing Demo project — understanding its architecture, tech stack, data model, or project structure. Reference it before making changes to models, views, services, or configuration.

## Технологический стек

- **Backend:** Python, Django 4.1.7
- **База данных:** PostgreSQL (psycopg2-binary)
- **Асинхронные задачи:** Celery 5.2.7 + Celery Beat (планировщик)
- **Брокер сообщений:** Redis
- **REST API:** Django REST Framework 3.14.0, django-filter
- **Внешний API:** tinkoff-investments (Tinkoff Invest API) — получение рыночных данных
- **Визуализация:** Plotly (графики исторических цен)
- **Frontend:** Django Templates, Bootstrap 3 (crispy-bootstrap3), jQuery, Font Awesome
- **Инфраструктура:** Docker Compose (PostgreSQL + Redis)
- **Форматирование кода:** Black, isort

## Структура проекта

| Папка / Файл | Назначение |
|---|---|
| `config/` | Корневой пакет Django: `settings.py`, `urls.py`, `celery.py`, WSGI/ASGI |
| `dashboard/` | Основное приложение — акции, views, сервисы, API, Celery-задачи |
| `dashboard/models.py` | Модель `Share` (акция) |
| `dashboard/views.py` | Класс-views: список, детали, CRUD акций |
| `dashboard/services/market_data.py` | Последняя цена акции через Tinkoff API |
| `dashboard/services/graph.py` | График исторических цен (Plotly, 180 дней) |
| `dashboard/tasks.py` | Celery-задача `update_last_price` — периодическое обновление цен |
| `dashboard/api/v1/` | REST API v1: ViewSet, Serializer, роутер |
| `dashboard/forms.py` | Django-форма для CRUD акций |
| `dashboard/admin.py` | Регистрация модели в Django Admin |
| `dashboard/management/commands/add_shares.py` | Загрузка списка акций из Tinkoff API |
| `dashboard/templates/dashboard/` | HTML-шаблоны: base, list, detail, create, delete |
| `user/` | Приложение аутентификации: регистрация, вход, выход |
| `user/forms.py` | Формы регистрации и авторизации |
| `user/views.py` | Views для login, registration, logout |
| `user/templates/user/` | HTML-шаблоны: auth, registration, base |
| `docker-compose.yml` | Контейнеры PostgreSQL и Redis |
| `requirements.txt` | Зависимости проекта |
| `manage.py` | Django-менеджер |

## Модель данных

### `Share` (dashboard/models.py)

| Поле | Тип | Описание |
|---|---|---|
| `figi` | CharField(255), unique | Идентификатор FIGI |
| `isin` | CharField(255) | Идентификатор ISIN |
| `name` | CharField(255) | Наименование компании |
| `ticker` | CharField(10), unique | Тикер акции |
| `currency` | CharField(20) | Валюта |
| `uid` | CharField(255), unique | UUID в Tinkoff API |
| `last_price` | FloatField, nullable | Текущая цена (Celery) |
| `is_trend_high` | BooleanField, nullable | Флаг роста/падения |
| `updated_at` | DateTimeField, auto_now | Время обновления |

### `User` (user/models.py)

Стандартная модель `django.contrib.auth.models.User`. Email используется как логин (username).

Связей между `Share` и `User` нет — модели независимы.

## Ключевые компоненты

| Компонент | Файл | Назначение |
|---|---|---|
| Модель Share | `dashboard/models.py` | Хранение данных об акциях |
| ShareListView | `dashboard/views.py:20-26` | Список акций (публичный) |
| ShareDetailView | `dashboard/views.py:29-38` | Детальная страница с графиком |
| CRUD-views | `dashboard/views.py:41-63` | Управление акциями (только авторизованные) |
| Auth views | `user/views.py:8-64` | Регистрация, вход, выход |
| Celery-задача | `dashboard/tasks.py:7-28` | Фоновое обновление цен |
| REST API | `dashboard/api/v1/` | Программный доступ к акциям |
| Management-команда | `dashboard/management/commands/add_shares.py` | Загрузка каталога из API |
| Admin | `dashboard/admin.py:6-19` | Административная панель |
