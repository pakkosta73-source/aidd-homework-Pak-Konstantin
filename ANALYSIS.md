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
- Celery Beat запускает задачу `update_last_price` каждые 5 минут (300 секунд).
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

1. **`SECRET_KEY`** (`config/settings.py:7`) — **ИСПРАВЛЕНО**: используется `os.getenv` с дефолтным значением для разработки.
2. **`DEBUG = False`** (`config/settings.py:9`) — **ИСПРАВЛЕНО**: режим отладки отключён.
3. **`ALLOWED_HOSTS`** (`config/settings.py:11`) — **ИСПРАВЛЕНО**: список заполнен (`localhost`, `127.0.0.1`).
4. **Пароль БД** (`config/settings.py:101`) — **ИСПРАВЛЕНО**: используется `os.getenv('DB_PASSWORD', 'postgres')`.
5. **`TINKOFF_TOKEN`** (`config/settings.py:135`) — **ИСПРАВЛЕНО**: используется `os.getenv('TINKOFF_TOKEN', '')`.
6. **Отсутствие аутентификации в REST API** — `ShareViewSet` не требует авторизации, любой может читать/писать/удалять акции через API. **НЕ ИСПРАВЛЕНО** — требует отдельной доработки.
7. **CSRF-защита** — шаблоны `auth.html` и `registration.html` содержат `{% csrf_token %}` — реализовано корректно.

### Дефекты реализации

8. **Логика определения тренда** (`dashboard/tasks.py:16-19`) — **ИСПРАВЛЕНО**: условие инвертировано — при росте цены (`last_price > share.last_price`) теперь устанавливается `is_trend_high = True`, при падении — `False`. Добавлена проверка `share.last_price is None` для первого запуска.
9. **TypeError при первом обновлении цены** (`dashboard/tasks.py:15-22`) — **ИСПРАВЛЕНО**: добавлена явная проверка `share.last_price is None` перед сравнением. При равных ценах сохраняется предыдущее значение тренда.
10. **Голые `except Exception`** (`dashboard/tasks.py`) — **ИСПРАВЛЕНО**: заменены на конкретные `TypeError`, `ValueError` с подробными лог-сообщениями, включающими ID акции.
11. **`ShareDetailView` принимает только GET** — класс наследуется от `View`, но реализует только `get()`. POST/PUT/DELETE запросы вернут 405 без пояснения. **НЕ ИСПРАВЛЕНО** — минимальное влияние на работоспособность.
12. **`RegistrationForm` — не оценённый queryset** (`user/forms.py:39`) — **ИСПРАВЛЕНО**: используется `.exists()` вместо QuerySet.
13. **`AuthView` не использует валидацию формы** (`user/views.py:17-19`) — **ИСПРАВЛЕНО**: добавлен вызов `form.is_valid()` и использование `form.cleaned_data` вместо `form.data`.
14. **`CELERY_BEAT_SCHEDULE` schedule = 10.0** (`config/celery.py:16`) — **ИСПРАВЛЕНО**: расписание изменено на 300 секунд (5 минут), название задачи обновлено на `update-prices-every-5-min`.
15. **`docker-compose.yml` не содержит Django-сервис** — в compose только PostgreSQL и Redis, но нет сервиса для самого приложения и Celery worker/beat. **НЕ ИСПРАВЛЕНО** — требует отдельной доработки.
16. **`ShareModelForm` exposes все поля** (`dashboard/forms.py:11`) — **ИСПРАВЛЕНО**: форма ограничена полем `name`, автозаполнение остальных полей (figi, isin, ticker, currency, uid) происходит через API Tinkoff при валидации.

### Устаревшие зависимости

15. **Django 4.1.7 → 5.2.3** — **ИСПРАВЛЕНО**: обновлён до актуальной LTS-версии.
16. **Django REST Framework 3.14.0 → 3.15.2** — **ИСПРАВЛЕНО**: обновлён до актуальной версии.
17. **tinkoff-investments** — **ИСПРАВЛЕНО**: установка из активного fork `RussianInvestments/invest-python@0.2.0-beta102` (оригинальный пакет удалён с PyPI).
18. **protobuf 3.20.3 → 4.25.5** — **ИСПРАВЛЕНО**: обновлён для совместимости с tinkoff-investments.
19. **pydantic 1.10.6 → 2.10.3** — **ИСПРАВЛЕНО**: обновлён до мажорной версии 2.x.
20. **celery 5.2.7 → 5.4.0** — **ИСПРАВЛЕНО**: обновлён до актуальной версии.
21. **redis 4.5.1 → 5.2.1** — **ИСПРАВЛЕНО**: обновлён до актуальной версии.
22. **plotly 5.13.1 → 5.24.1** — **ИСПРАВЛЕНО**: обновлён в пределах 5.x для совместимости с `plotly.offline`.
23. **crispy-bootstrap3 → crispy-bootstrap5 2024.2** — **ИСПРАВЛЕНО**: заменён на Bootstrap 5.
24. **jQuery 3.3.1 → Bootstrap 5.3.3 bundle (CDN)** — **ИСПРАВЛЕНО**: шаблоны обновлены.

### Архитектурные проблемы

25. **Нет разделения на env-файлы** — секреты (токены, пароли, ключи) хранятся в `settings.py` через `os.getenv`. **ЧАСТИЧНО ИСПРАВЛЕНО**: добавлены `os.getenv` для SECRET_KEY, DB_PASSWORD, TINKOFF_TOKEN. Полное разделение на env-файлы требует отдельной доработки.
26. **Нет миграций для пользовательского приложения** — `user/migrations/__init__.py` пуст, приложение использует стандартную модель User без кастомизации. **НЕ ИСПРАВЛЕНО**.
27. **Нет тестов для бизнес-логики** — тесты покрывают только API CRUD, но не Celery-задачи, сервисы, формы регистрации/авторизации. **НЕ ИСПРАВЛЕНО**.
28. **Нет rate limiting для API** — REST API не ограничивает количество запросов. **НЕ ИСПРАВЛЕНО**.
29. **`ShareModelForm` exposes все поля** — **ИСПРАВЛЕНО**: форма ограничена полем `name`, остальные поля заполняются через API Tinkoff.
30. **Дублирование кода подключения к Tinkoff API** — `Client(TINKOFF_TOKEN)` создаётся отдельно в `market_data.py`, `graph.py`, `add_shares.py`, `forms.py`. **НЕ ИСПРАВЛЕНО** — требует выноса в отдельный сервис.

---

## 6. Исправленные дефекты (сводка)

| # | Дефект | Файл | Статус |
|---|---|---|---|
| D-1 | Инвертированная логика тренда | `dashboard/tasks.py` | ✅ Исправлено |
| D-2 | TypeError при None цене | `dashboard/tasks.py` | ✅ Исправлено |
| D-3 | Голые `except Exception` | `dashboard/tasks.py` | ✅ Исправлено |
| D-4 | RegistrationForm — не оценённый queryset | `user/forms.py` | ✅ Исправлено |
| D-5 | AuthView без валидации формы | `user/views.py` | ✅ Исправлено |
| D-6 | Celery schedule = 10 секунд | `config/celery.py` | ✅ Исправлено |
| D-8 | ShareModelForm exposes все поля | `dashboard/forms.py` | ✅ Исправлено |
| S-1 | SECRET_KEY в коде | `config/settings.py` | ✅ Исправлено |
| S-2 | DEBUG = True | `config/settings.py` | ✅ Исправлено |
| S-3 | ALLOWED_HOSTS пустой | `config/settings.py` | ✅ Исправлено |
| S-4 | Hardcoded пароль БД | `config/settings.py` | ✅ Исправлено |
| S-5 | Hardcoded TINKOFF_TOKEN | `config/settings.py` | ✅ Исправлено |
| Dep | Устаревшие зависимости | `requirements.txt` | ✅ Исправлено |
