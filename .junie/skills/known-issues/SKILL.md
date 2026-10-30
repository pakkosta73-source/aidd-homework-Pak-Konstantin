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

## Устаревшие зависимости

| Пакет | Текущая версия | Актуальная версия |
|---|---|---|
| Django | 4.1.7 (EOL) | 4.2.x / 5.1.x |
| Django REST Framework | 3.14.0 | 3.15.x |
| tinkoff-investments | 0.2.0b50 (бета) | — |
| protobuf | 3.20.3 | Может конфликтовать с новыми tinkoff-investments |
| pydantic | 1.10.6 | 2.x |
| celery | 5.2.7 | 5.4.x |
| redis | 4.5.1 | 5.x |
| plotly | 5.13.1 | 6.x |
| crispy-bootstrap3 | Bootstrap 3 (устарел) | Bootstrap 5 |
| jQuery | 3.3.1 | 3.7.x |

## Архитектурные проблемы

- Нет разделения на env-файлы — все секреты в `settings.py`.
- Нет миграций для пользовательского приложения — `user/migrations/__init__.py` пуст.
- Нет тестов для бизнес-логики — тесты только API CRUD, не Celery-задачи, сервисы, формы.
- Нет rate limiting для API.
- Дублирование кода подключения к Tinkoff API — `Client(TINKOFF_TOKEN)` в `market_data.py`, `graph.py` и `add_shares.py`.
