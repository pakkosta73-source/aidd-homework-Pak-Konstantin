---
name: known-issues
description: Known issues, security vulnerabilities, implementation defects, outdated dependencies, and architectural problems for the Investing Demo application.
---
# Investing Demo — Known Issues

**Trigger:** Use this skill when debugging, fixing bugs, reviewing security, or refactoring the Investing Demo project. Reference before making changes that could be affected by known defects.

## Критические проблемы безопасности

1. **Пустой `SECRET_KEY`** — `config/settings.py:6`. Приложение не запустится или будет уязвимо.
2. **`DEBUG = True`** — `config/settings.py:8`. Режим отладки в продакшене.
3. **`ALLOWED_HOSTS = []`** — `config/settings.py:10`. Пустой список заблокирует запросы при `DEBUG=False`.
4. **Hardcoded пароль БД** — `config/settings.py:100`. Пароль `postgres` зашит в коде.
5. **Пустой `TINKOFF_TOKEN`** — `config/settings.py:134`. Токен API зашит в коде.
6. **Отсутствие аутентификации в REST API** — `ShareViewSet` не требует авторизации.
7. **CSRF-защита** — Шаблоны `auth.html` и `registration.html` содержат `{% csrf_token %}` — реализовано корректно.

## Дефекты реализации

### D-1: Инвертированная логика определения тренда
`dashboard/tasks.py:16-19` — условие `share.last_price > last_price` устанавливает `is_trend_high = False` при росте и `True` при падении. Зелёный фон отображается при падении цены, красный — при росте.

### D-2: TypeError при первом обновлении цены
`dashboard/tasks.py:15-22` — когда `share.last_price = None`, сравнение вызывает `TypeError`. Голый `except Exception` молча устанавливает `is_trend_high = True`.

### D-3: Голые `except Exception`
`tasks.py` и `graph.py` — широкие исключения скрывают реальные ошибки.

### D-4: `RegistrationForm` — не оценённый queryset
`user/forms.py:39` — `User.objects.filter(email=email)` возвращает QuerySet, который всегда истинен в `if user:` → регистрация нового пользователя всегда падает с ошибкой «email уже зарегистрирован».
**Фикс:** Использовать `.exists()` или `.first()`.

### D-5: `AuthView` не использует валидацию формы
`user/views.py:17-19` — `form.data` без `form.is_valid()` может вызвать `KeyError`.

### D-6: `CELERY_BEAT_SCHEDULE` schedule = 10.0
`config/celery.py:16` — Чрезмерная нагрузка на Tinkoff API. Название задачи `add-every-5-min` не соответствует расписанию.

### D-7: `docker-compose.yml` без Django-сервиса
Только PostgreSQL и Redis, нет сервиса приложения и Celery worker/beat.

### D-8: `ShareModelForm` exposes все поля
`dashboard/forms.py:11` — `fields = "__all__"`. Пользователь может подменить `last_price`, `is_trend_high`, `uid`, `figi`.

## Устаревшие зависимости (обновлено 30.10.2026)

Все устаревшие зависимости обновлены в `requirements.txt`. Ниже приведён список произведённых изменений:

| Пакет | Было | Стало | Примечание |
|---|---|---|---|
| Django | 4.1.7 (EOL, декабрь 2023) | 5.2.3 (LTS) | LTS до апреля 2028 |
| Django REST Framework | 3.14.0 | 3.15.2 | |
| pydantic | 1.10.6 | 2.10.3 | Breaking changes: v1 → v2 |
| protobuf | 3.20.3 | 4.25.5 | Понизил для совместимости с tinkoff-investments (требует <5.0.0) |
| grpcio | 1.51.3 | 1.68.1 | |
| celery | 5.2.7 | 5.4.0 | |
| kombu | 5.2.4 | 5.4.2 | |
| amqp | 5.1.1 | 5.3.1 | |
| billiard | 3.6.4.0 | 4.2.1 | |
| vine | 5.0.0 | 5.1.0 | |
| redis | 4.5.1 | 5.2.1 | |
| plotly | 5.13.1 | 5.24.1 | Оставлен 5.x для совместимости с `plotly.offline` |
| psycopg2-binary | 2.9.5 | 2.9.10 | |
| asgiref | 3.6.0 | 3.8.1 | |
| sqlparse | 0.4.3 | 0.5.2 | |
| django-filter | 22.1 | 24.3 | |
| django-crispy-forms | 2.0 | 2.3 | |
| crispy-bootstrap3 | 2022.1 | crispy-bootstrap5 2024.2 | Заменён на Bootstrap 5 |
| black | 23.1.0 | 24.8.0 | |
| isort | 5.12.0 | 5.13.2 | |
| click | 8.1.3 | 8.1.7 | |
| cachetools | 5.3.0 | 5.5.0 | |
| tenacity | 8.2.2 | 9.0.0 | |
| typing_extensions | 4.5.0 | 4.15.0 | |
| pytz | 2022.7.1 | 2024.2 | |
| prompt-toolkit | 3.0.38 | 3.0.47 | |
| platformdirs | 3.1.1 | 4.3.6 | |
| pathspec | 0.11.1 | 0.12.1 | |
| packaging | 23.0 | 24.2 | |
| mypy-extensions | 1.0.0 | 1.1.0 | |
| tomli | 2.0.1 | 2.0.2 | |
| wcwidth | 0.2.6 | 0.2.13 | |
| async-timeout | 4.0.2 | 5.0.1 | |
| click-didyoumean | 0.3.0 | 0.3.1 | |
| click-repl | 0.2.0 | 0.3.0 | |

### tinkoff-investments — удалён с PyPI

Пакет `tinkoff-investments` был удалён с PyPI в декабре 2025. Оригинальный репозиторий `Tinkoff/invest-python` архивирован. В `requirements.txt` указана установка из активного fork: `git+https://github.com/RussianInvestments/invest-python.git@0.2.0-beta102`.

### Проблемы установки зависимостей (исправлено 30.10.2026)

При установке `pip install -r requirements.txt` возникали две проблемы:

1. **`tinkoff==0.1.1` недоступен на PyPI** — пакет удалён. `tinkoff-investments` зависит от `tinkoff>=0.1.1,<0.2.0`, однако в коде проекта импортируется только `tinkoff.invest` (предоставляется `tinkoff-investments`), поэтому зависимость можно игнорировать.
2. **Конфликт protobuf** — `tinkoff-investments` требует `protobuf>=4.25.1,<5.0.0`. Понизил protobuf с 5.28.3 до 4.25.5.

Для установки выполните: `pip install -r requirements.txt`.

### Обновлённые шаблоны

- `dashboard/templates/dashboard/base.html`: jQuery 3.3.1 + Popper.js 1.14.6 → Bootstrap 5.3.3 bundle (CDN)
- `user/templates/user/base.html`: локальный Bootstrap 5.1.3 → Bootstrap 5.3.3 (CDN)
- `config/settings.py`: `crispy_bootstrap3` → `crispy_bootstrap5`, `CRISPY_TEMPLATE_PACK = "bootstrap5"`

## Архитектурные проблемы

- Нет разделения на env-файлы — все секреты в `settings.py`.
- Нет миграций для пользовательского приложения — `user/migrations/__init__.py` пуст.
- Нет тестов для бизнес-логики — тесты только API CRUD, не Celery-задачи, сервисы, формы.
- Нет rate limiting для API.
- Дублирование кода подключения к Tinkoff API — `Client(TINKOFF_TOKEN)` в `market_data.py`, `graph.py` и `add_shares.py`.
