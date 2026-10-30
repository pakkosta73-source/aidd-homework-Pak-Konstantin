# ANALYSIS.md — Investing Demo

## 1. Технологический стек и назначение приложения

**Назначение:** Веб-приложение для мониторинга рыночных цен акций через API брокера Тинькофф Инвестиции. Пользователи могут просматривать список акций, их текущие цены, тренды и исторические графики.

**Технологический стек:**

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

---

## 2. Структура проекта и роль основных папок/файлов

| Папка / Файл | Назначение |
|---|---|
| `config/` | Корневой пакет Django: настройки (`settings.py`), URL-маршруты (`urls.py`), Celery (`celery.py`), WSGI/ASGI |
| `dashboard/` | Основное приложение — управление акциями, views, сервисы, API, Celery-задачи |
| `dashboard/models.py` | Модель данных `Share` (акция) |
| `dashboard/views.py` | Класс-views: список, детали, CRUD акций |
| `dashboard/services/market_data.py` | Получение последней цены акции через Tinkoff API |
| `dashboard/services/graph.py` | Построение графика исторических цен (Plotly, 180 дней) |
| `dashboard/tasks.py` | Celery-задача `update_last_price` — периодическое обновление цен |
| `dashboard/api/v1/` | REST API v1: ViewSet, Serializer, роутер для акций |
| `dashboard/forms.py` | Django-форма для создания/редактирования акций |
| `dashboard/admin.py` | Регистрация модели в Django Admin |
| `dashboard/management/commands/add_shares.py` | Management-команда для загрузки списка акций из Tinkoff API |
| `dashboard/templates/dashboard/` | HTML-шаблоны: base, list, detail, create, delete |
| `user/` | Приложение аутентификации: регистрация, вход, выход |
| `user/forms.py` | Формы регистрации и авторизации |
| `user/views.py` | Views для login, registration, logout |
| `user/templates/user/` | HTML-шаблоны: auth, registration, base |
| `docker-compose.yml` | Контейнеры PostgreSQL и Redis |
| `requirements.txt` | Зависимости проекта |
| `manage.py` | Стандартный Django-менеджер |

---

## 3. Модель данных

### Модель `Share` (dashboard/models.py)

| Поле | Тип | Описание |
|---|---|---|
| `figi` | CharField(255), unique | Идентификатор FIGI инструмента |
| `isin` | CharField(255) | Идентификатор ISIN |
| `name` | CharField(255) | Наименование компании |
| `ticker` | CharField(10), unique | Тикер акции |
| `currency` | CharField(20) | Валюта |
| `uid` | CharField(255), unique | UUID инструмента в Tinkoff API |
| `last_price` | FloatField, nullable | Текущая цена (обновляется Celery-задачей) |
| `is_trend_high` | BooleanField, nullable | Флаг роста/падения цены |
| `updated_at` | DateTimeField, auto_now | Время последнего обновления записи |

### Модель `User` (user/models.py)

Используется стандартная модель `django.contrib.auth.models.User` через `get_user_model()`. Email используется как логин (username).

### Связи между моделями

Связей между моделями **нет**. `Share` и `User` независимы — нет связи «пользователь → портфель → акции».

---

## 4. Восстановленные функциональные требования

### FR-1: Просмотр списка акций
- Любой пользователь (в т.ч. неавторизованный) может просматривать пагинированный список всех акций с тикером, названием, ISIN и текущей ценой.
- Цена отображается с цветовой индикацией: зелёный фон — рост, красный — падение.
- **Подтверждение:** `ShareListView`, шаблон `list.html`.

### FR-2: Просмотр детальной информации об акции
- Любой пользователь может открыть страницу акции с текущей ценой, временем обновления и графиком исторических цен за последние 180 дней.
- График строится через Tinkoff Invest API (дневные свечи) и рендерится через Plotly.
- **Подтверждение:** `ShareDetailView`, `services/graph.py`, шаблон `detail.html`.

### FR-3: Регистрация пользователя
- Гость может зарегистрироваться, указав email и пароль (с подтверждением).
- При регистрации проверяется уникальность email и совпадение паролей.
- После регистрации пользователь автоматически авторизуется.
- **Подтверждение:** `RegistrationView`, `RegistrationForm`, `user/forms.py`.

### FR-4: Авторизация пользователя
- Пользователь может войти по email и паролю.
- При неудачной попытке отображается сообщение об ошибке.
- **Подтверждение:** `AuthView`, `AuthForm`.

### FR-5: Выход из системы
- Авторизованный пользователь может выйти из системы.
- **Подтверждение:** `LogoutView`.

### FR-6: Управление акциями (CRUD) — только для авторизованных пользователей
- Авторизованный пользователь может добавлять, редактировать и удалять записи об акциях.
- Кнопки «Добавить», «Редактировать», «Удалить» видны только авторизованным.
- **Подтверждение:** `IsUserAuthenticatedMixin`, `ShareCreateView`, `ShareUpdateView`, `ShareDeleteView`.

### FR-7: Периодическое обновление рыночных цен
- Celery Beat запускает задачу `update_last_price` каждые 10 секунд.
- Задача обращается к Tinkoff API, получает последние цены и обновляет `last_price` и `is_trend_high` для всех акций.
- **Подтверждение:** `config/celery.py` (beat_schedule), `dashboard/tasks.py`.

### FR-8: REST API для акций
- Доступен REST API по адресу `/api/v1/shares/` с поддержкой CRUD операций.
- Поддерживается пагинация (LimitOffset, 100 записей), фильтрация по `name` и `ticker`, сортировка, поиск по `name`.
- **Подтверждение:** `dashboard/api/v1/views.py`, `serializer.py`, `router.py`.

### FR-9: Загрузка каталога акций из Tinkoff API
- Management-команда `add_shares` загружает полный список доступных акций из Tinkoff Invest API в базу данных.
- **Подтверждение:** `dashboard/management/commands/add_shares.py`.

### FR-10: Django Admin панель
- Администратор может просматривать, искать и редактировать акции через Django Admin.
- **Подтверждение:** `dashboard/admin.py`.

---

## 5. Явные проблемы, устаревшие зависимости и дефекты

### Критические проблемы безопасности

1. **Пустой `SECRET_KEY`** (`config/settings.py:6`) — приложение не запустится или будет крайне уязвимо.
2. **`DEBUG = True`** (`config/settings.py:8`) — режим отладки в продакшене exposes стек-трейсы и настройки.
3. **`ALLOWED_HOSTS = []`** (`config/settings.py:10`) — пустой список при `DEBUG=False` заблокирует все запросы.
4. **Hardcoded пароль БД** (`config/settings.py:100`) — пароль `postgres` зашит в коде.
5. **Пустой `TINKOFF_TOKEN`** (`config/settings.py:134`) — токен API зашит в коде, пустой по умолчанию.
6. **Отсутствие аутентификации в REST API** — `ShareViewSet` не требует авторизации, любой может читать/писать/удалять акции через API.
7. **Отсутствие CSRF-защиты в формах** — формы регистрации и авторизации не используют `{% csrf_token %}` в шаблонах (проверить шаблоны auth.html/registration.html).

### Дефекты реализации

8. **Логика определения тренда** (`dashboard/tasks.py:16-19`) — сравнение `share.last_price > last_price` выдаёт `is_trend_high = False` при падении и `True` при росте, но при первом запуске (`last_price = None`) возникает `TypeError`, который ловится голым `except Exception` и молча устанавливает `True`.
9. **Голые `except Exception`** — в `tasks.py` и `graph.py` используются широкие исключения, которые скрывают реальные ошибки.
10. **`ShareDetailView` принимает только GET** — класс наследуется от `View`, но реализует только `get()`. POST/PUT/DELETE запросы вернут 405 без пояснения.
11. **`RegistrationForm` — `user` queryset не оценён** (`user/forms.py:39`) — `user = User.objects.filter(email=email)` возвращает QuerySet, который всегда истинен в `if user:` даже при пустом результате → **регистрация нового пользователя всегда падает с ошибкой «email уже зарегистрирован»**.
12. **`AuthView` не использует валидацию формы** (`user/views.py:17-19`) — `form.data` используется напрямую без `form.is_valid()`, что может вызвать KeyError при пустых полях.
13. **`CELERY_BEAT_SCHEDULE` schedule = 10.0** (`config/celery.py:16`) — задача запускается каждые 10 секунд, что создаёт чрезмерную нагрузку на Tinkoff API. Название задачи `add-every-5-min` не соответствует реальному расписанию.
14. **`docker-compose.yml` не содержит Django-сервис** — в compose только PostgreSQL и Redis, но нет сервиса для самого приложения и Celery worker/beat.

### Устаревшие зависимости

15. **Django 4.1.7** — EOL с апреля 2023. Актуальная LTS — 4.2.x / 5.1.x.
16. **Django REST Framework 3.14.0** — устаревшая версия, актуальная 3.15.x.
17. **tinkoff-investments 0.2.0b50** — бета-версия, может содержать нестабильный API.
18. **protobuf 3.20.3** — устаревшая версия, может конфликтовать с новыми версиями tinkoff-investments.
19. **pydantic 1.10.6** — устаревшая мажорная версия, актуальная 2.x.
20. **celery 5.2.7** — актуальная 5.4.x.
21. **redis 4.5.1** — актуальная 5.x.
22. **plotly 5.13.1** — актуальная 6.x.
23. **crispy-bootstrap3** — использует Bootstrap 3, который устарел (Bootstrap 5 — актуальный).
24. **jQuery 3.3.1** в шаблонах — устаревшая версия, актуальная 3.7.x.

### Архитектурные проблемы

25. **Нет разделения на env-файлы** — все секреты (токены, пароли, ключи) хранятся в `settings.py`.
26. **Нет миграций для пользовательского приложения** — `user/migrations/__init__.py` пуст, приложение использует стандартную модель User без кастомизации.
27. **Нет тестов для бизнес-логики** — тесты покрывают только API CRUD, но не Celery-задачи, сервисы, формы регистрации/авторизации.
28. **Нет rate limiting для API** — REST API не ограничивает количество запросов.
29. **`ShareModelForm` exposes все поля** (`fields = "__all__"`) — включая `last_price`, `is_trend_high`, `uid`, `figi` — пользователь может вручную подменить системные поля.
30. **Дублирование кода подключения к Tinkoff API** — `Client(TINKOFF_TOKEN)` создаётся отдельно в `market_data.py` и `graph.py`.
