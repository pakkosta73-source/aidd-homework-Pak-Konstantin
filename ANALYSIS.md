# ANALYSIS.md — анализ исходного кода «Investing Demo»

## 1. Технологический стек и назначение приложения

**Назначение:** простой веб-дашборд для торгового терминала Tinkoff Invest API.
Приложение загружает список акций с биржи, позволяет просматривать их текущие цены и графики за 180 дней, вести CRUD-управление инструментами и обновляет цены в фоне через Celery.

**Стек:**
- Python / Django 4.1.7 (монолит, server-rendered шаблоны + REST API)
- Django REST Framework 3.14.0, django-filter 22.1
- PostgreSQL (psycopg2-binary 2.9.5, БД `investing`), Redis 4.5.1 (брокер Celery 5.2.7)
- Tinkoff Invest API SDK: `tinkoff-investments 0.2.0b50` (+ `grpcio`, `pydantic`, `protobuf`)
- Plotly 5.13.1 — серверный рендеринг графиков свечей
- django-crispy-forms 2.0 + crispy-bootstrap3 (рендеринг форм)
- Docker Compose: только инфраструктура (postgres, redis); само приложение запускается вне Docker

## 2. Структура проекта

- `manage.py` — стандартная точка входа Django.
- `config/` — корневой пакет проекта:
  - `settings.py` — вся конфигурация (БД, DRF, Celery, логирование, токены — жёстко в коде);
  - `urls.py` — маршрутизация: `admin/`, `""` → dashboard, `user` → приложение user;
  - `celery.py` — экземпляр Celery + beat-расписание задачи обновления цен;
  - `wsgi.py` / `asgi.py` — стандартные entry-point'ы.
- `dashboard/` — основное приложение (акции):
  - `models.py` — модель `Share`;
  - `views.py` — CBV: список/детализация/CRUD акций (HTML);
  - `forms.py` — `ShareModelForm` (ModelForm со всеми полями);
  - `urls.py` — страницы dashboard + include API;
  - `admin.py` — регистрация `Share` в админке;
  - `tasks.py` — Celery-задача `update_last_price`;
  - `services/` — интеграция со сторонними API:
    - `market_data.py` — запрос последних цен (Tinkoff);
    - `graph.py` — построение Plotly-графика свечей;
  - `api/v1/` — REST API: `router.py` (DRF Router), `views.py` (`ShareViewSet` + фильтры), `serializer.py`, `urls.py`;
  - `management/commands/add_shares.py` — первичный импорт всех акций из Tinkoff в БД;
  - `templates/dashboard/` — `base.html`, `list.html`, `detail.html`, `create.html`, `delete.html`;
  - `migrations/` — 7 миграций (создание модели, uuid, last_price, verbose_name, updated_at);
  - `tests.py` — тесты HTML-списка и REST API (CRUD, фильтры).
- `user/` — приложение аутентификации (своей модели нет, используется стандартный `django.contrib.auth.models.User`):
  - `views.py` — `AuthView`, `RegistrationView`, `LogoutView` (функциональные View-классы);
  - `forms.py` — `RegistrationForm`, `AuthForm`;
  - `templates/user/` + статика для форм входа/регистрации.
- `docker-compose.yml` — postgres + redis.
- `README.md` — инструкция запуска (docker, миграции не упомянуты, но есть команда `add_shares`, celery worker/beat).
- `requirements.txt` — фиксированные зависимости (без dev-разделителя: и рантайм, и black/isort/mypy-extensions вместе).

## 3. Модель данных

- **`dashboard.models.Share` — акция (единственная сущность приложения; связей FK/M2M нет):**
  - `figi` — CharField(255), уникальный — идентификатор инструмента Tinkoff;
  - `isin` — CharField(255) — международный идентификационный код ценной бумаги;
  - `name` — CharField(255), verbose_name «Наименование компании»;
  - `ticker` — CharField(10), уникальный;
  - `currency` — CharField(20), verbose_name «Валюта»;
  - `uid` — CharField(255), уникальный (добавлен миграцией 0003) — UUID инструмента Tinkoff;
  - `last_price` — FloatField, nullable (миграция 0004) — последняя цена;
  - `is_trend_high` — BooleanField, nullable (миграция 0004) — признак «цена растёт / выросла»;
  - `updated_at` — DateTimeField(auto_now=True), nullable (миграция 0007).
- **Пользователь** — стандартная модель Django (`User`); приложение `user` с собственной моделью объявлено, но кастомная модель не определена и `AUTH_USER_MODEL` не переопределён (в `user/models.py` лишь `User = get_user_model()`; миграций у приложения нет).
- Схема БД формируется миграциями `dashboard/migrations/0001–0007`; при регистрации username = email.

## 4. Восстановленные функциональные требования

1. **Просмотр списка акций** (доступен анонимным пользователям): таблица «Тикер / Название / ISIN / Текущая цена», пагинация по 100 записей, сортировка по названию (см. `ShareListView`, `templates/dashboard/list.html`).
2. **Визуализация тренда цены:** цена подсвечивается зелёным при `is_trend_high=True` и красным при `False` (см. `list.html`).
3. **Просмотр карточки акции:** страница `/<pk>` с Plotly-графиком цен закрытия дневных свечей за последние 180 дней из Tinkoff Invest API (`ShareDetailView`, `services/graph.py`).
4. **Регистрация пользователя** (`/user/registration/`): ввод e-mail и пароля; бизнес-правила — пароль должен совпадать с подтверждением, e-mail не должен быть уже зарегистрирован; после успешной регистрации происходит автоматический логин и редирект на список акций (`user/forms.py`, `user/views.py`).
5. **Авторизация** (`/user/login/`) по e-mail (username = email) и паролю; ошибка — сообщение «Неверный логин или пароль».
6. **Выход** (`/user/logout/`) — завершение сессии, редирект на список.
7. **CRUD акций авторизованными пользователями:** создание (`/create`), редактирование (`/update/<pk>`), удаление (`/delete/<pk>`) — только для аутентифицированных пользователей (миксин `IsUserAuthenticatedMixin`, неаутентифицированных без ошибки редиректит на главную); анонимным доступны только просмотр.
8. **Автоматическое обновление цен:** Celery-задача `update_last_price` периодически (по beat-расписанию из `config/celery.py`) запрашивает последнюю цену каждой акции через Tinkoff API, сохраняет её в `last_price` и выставляет `is_trend_high` (новая цена выше старой → цена растёт); ошибки логируются в файл `app.logs`.
9. **Первоначальная загрузка справочника акций:** management-команда `python manage.py add_shares` импортирует все доступные акции Tinkoff в БД (`get_or_create` по figi).
10. **REST API `/api/v1/shares/`:** полный CRUD через `ShareViewSet` (DRF ModelViewSet, DefaultRouter), пагинация LimitOffset по 100, возможность фильтрации по `name`, `ticker`, поиска и сортировки по `name`/`ticker` (маршруты вида `api/v1/shares/…`).
11. **Административная панель:** модель `Share` зарегистрирована в admin с поиском и отображением основных полей.

## 5. Явные проблемы, дефекты и устаревшие зависимости

### Критичные дефекты кода
- **Потеря точности цен:** `market_data.py` и `graph.py` берут только `price.units`, игнорируя `nano` — цена округляется до целых рублей (и для копеечных цен становится грубо неверной).
- **`is_trend_high` по умолчанию `True` при любой ошибке сравнения** (`tasks.py`, строки 16–22): при отсутствии прежней цены акция помечается как «растущая» — на UI вводит пользователя в заблуждение.
- **Несогласованность beat-расписания:** задача называется «add-every-5-min», но `schedule=10.0` — фактический интервал 10 секунд (каждые 10 сек ходим в API по всем акциям).
- **Не обрабатывается 404 в `ShareDetailView`:** `Share.objects.get(id=pk)` при несуществующем pk кидает `DoesNotExist` → ошибка 500 вместо 404.
- **Доступ к API полностью анонимный:** `ShareViewSet` без `permission_classes` (по умолчанию AllowAny) — любой посетитель может создавать/удалять акции через API, минуя HTML-страницы с миксинами аутентификации; несогласованность приватности UI и API.
- **`ShareModelForm` с `fields="__all__"`:** форма позволяет вручную править `figi`, `uid`, `isin` — идентификаторы, привязанные к внешнему API.
- **`RegistrationForm.save()`:** создаёт пользователя и тут же `authenticate(...)`, но `first_name`/`password validation` Django-password-валидаторы пропускаются (форма не использует `UserCreationForm`, валидаторы паролей из `settings.py` не вызываются); сообщения об ошибках достаются через `form.errors["__all__"]` — хрупкая и нестандартная схема.
- **`update_last_price`:** N-запросов к API по одному на акцию (новый gRPC-клиент на каждую итерацию) + N отдельных `update` в цикле; весь список (сотни акций) переписывается каждые 10 секунд.

### Конфиденциальность / безопасность
- **Пустой `SECRET_KEY` и `DEBUG = True`, `ALLOWED_HOSTS = []`** в `settings.py` — конфигурация не боевая и небезопасная.
- **Токен `TINKOFF_TOKEN` жёстко прописан в `settings.py`;** там же учётные данные БД (`postgres/postgres`), пароли и креды продублированы в docker-compose; нет `.env` / переменных окружения.
- **CRUD-редактирование не ограничено правами:** любой аутентифицированный пользователь может удалить/изменить любую акцию (нет понятия владельца, всё общее).
- Логирование в файл `app.logs` в корне проекта (может попасть в git; собственный форматер логов неполный).

### Устаревшие/проблемные зависимости
- **Django 4.1.7** — ветка 4.1 снята с поддержки (EOL); актуальны 4.2 LTS / 5.x.
- **`tinkoff-investments 0.2.0b50`** — пре-релиз beta; пакет давно переехал в отдельные версии (`tinkoff-invest-python`), возможно, уже несовместим с текущим API.
- **DRF 3.14.0**, **django-filter 22.1**, **celery 5.2.7/kombu 5.2.4** — устаревшие версии (у kombu 5.2 есть известные проблемы совместимости); Redis 4.5.1, protobuf 3.20.3, pydantic 1.x, plotly 5.13.1 — все морально устарели.
- **psycopg2-binary** — для продакшена рекомендуют исходный `psycopg2` (или `psycopg` 3.x).
- `crispy-bootstrap3` / Bootstrap 3 template pack — устаревший UI-стек; в `base.html` с CDN подключён `plotly-latest.min.js` (эта ссылка давно deprecated), jQuery 3.3 и popper 1.14.6.
- В `requirements.txt` вперемешку рантайм-зависимости и инструменты разработки (black, isort, mypy-extensions), нет разделения на runtime/dev.
- Миксин `IsUserAuthenticatedMixin.handle_no_permission` переопределён безусловно (в т.ч. для POST) — тихий редирект вместо 403/логина.
- Отсутствует Dockerfile: приложение запускается только вручную вне Docker, compose не включает веб-сервис.
- Тесты покрывают только HTML-список и REST API; бизнес-логика (задача обновления цен, формы регистрации, сервисы Tinkoff) тестами не покрыта.
- В `graph.py` история свечей за 180 дней запрашивается у Tinkoff синхронно при каждом открытии карточки, без кеширования — медленная загрузка и лишняя нагрузка на API.
