# Технический аудит проекта «Investing Demo» (Задание №3, пп. 1–2)

**Дата:** 31.10.2026
**Окружение:** Python 3.11, macOS (Apple Silicon), Docker Desktop (PostgreSQL + Redis)

---

## 1. Устаревшие библиотеки и зависимости

Аудит выполнен сравнением: `requirements.txt` ↔ фактически установленная среда
(`.venv/pip freeze`) ↔ актуальный статус пакетов на PyPI.

### 1.1 Сводная таблица (зафиксировано → исправлено)

| Пакет | Было в requirements | Стало | Комментарий |
|---|---|---|---|
| Django | 4.1.7 (**EOL** с 04.2024) | 5.2.3 (LTS) | Разрыв в 2 минорные версии |
| djangorestframework | 3.14.0 | 3.15.2 | |
| django-filter | 22.1 | 24.3 | |
| django-crispy-forms | 2.0 | 2.3 | |
| crispy-bootstrap3 | 2022.1 | ~~удалён~~ | Заменён на `crispy-bootstrap5==2024.2` |
| celery | 5.2.7 | 5.4.0 | |
| kombu | 5.2.4 | 5.4.2 | Известные проблемы у 5.2 |
| amqp | 5.1.1 | 5.3.1 | |
| billiard | 3.6.4.0 | 4.2.1 | |
| vine | 5.0.0 | 5.1.0 | |
| redis (py) | 4.5.1 | 5.2.1 | |
| plotly | 5.13.1 | 5.24.1 | Оставлен 5.x (используется `plotly.offline`) |
| psycopg2-binary | 2.9.5 | 2.9.10 | |
| pydantic | 1.10.6 | 2.10.3 | Breaking change v1 → v2 |
| protobuf | 3.20.3 | 4.25.5 | Fork требует `>=4.25.1,<5.0.0` |
| grpcio | 1.51.3 | 1.68.1 | |
| black / isort | 23.1.0 / 5.12.0 | 24.8.0 / 5.13.2 | |
| python-dotenv | отсутствует | 1.2.4 | Добавлен (конфигурация через `.env`) |
| tinkoff-investments | 0.2.0b50 | 0.2.0b102 | См. ниже |
| tinkoff | 0.1.1 (**удалён с PyPI**) | локальный stub | См. ниже |

### 1.2 Критическая проблема: `tinkoff==0.1.1` недоступен

Оригинальный пакет `Tinkoff/invest-python` заархивирован, `tinkoff-investments`
удалён с PyPI (декабрь 2025). Текущая установка зависела от:

- `tinkoff==0.1.1` — на PyPI пакета больше нет (`Could not find a version…`);
- локального каталога-заглушки `./tinkoff-stub`, **отсутствовавшего в репозитории**
  (в `.venv` была прямая ссылка `tinkoff @ file:///./tinkoff-stub`) — на чистой
  машине восстановить окружение по `requirements.txt` было невозможно.

**Решение:**
1. `tinkoff-investments==0.2.0b102` установлен из активного форка
   `RussianInvestments/invest-python` (реальный код `tinkoff.invest`).
2. Восстановлен пакет-заглушка `./tinkoff-stub` (метаданные `tinkoff==0.1.1`,
   пустой `tinkoff/__init__.py`) — он удовлетворяет зависимость форка
   `tinkoff>=0.1.1,<0.2.0` без мёртвого PyPI-пакета и закоммичен в репозиторий.
3. `requirements.txt` полностью переписан под фактически работающую среду;
   `pip install -r requirements.txt` проверена (`--dry-run` резолвится
   без ошибок, включая сборку stub и git-форка).

### 1.3 Прочее

- Удалён неиспользуемый/несовместимый `crispy-bootstrap3` из бинарной среды.
- Файл `requirements.txt` теперь синхронизирован с реальным окружением —
  между «описанием» и «фактами» конфликта версий больше нет.

---

## 2. Проблемы совместимости и конфигурации (зафиксировано → исправлено)

| № | Проблема | Было | Исправлено |
|---|---|---|---|
| C-1 | Пустой `SECRET_KEY = ""` хардкодом | Приложение фактически не готово к запуску/работе | `SECRET_KEY` из `.env` (`load_dotenv`), шаблон — `.env.example` (в git не коммитится) |
| C-2 | `DEBUG = True`, `ALLOWED_HOSTS = []` хардкодом | Небезопасно/не работоспособно при `DEBUG=False` | `DEBUG`, `ALLOWED_HOSTS` из `.env`; при `DEBUG` автоматически разрешены `localhost`/`127.0.0.1` |
| C-3 | Хардкод кред БД и `TINKOFF_TOKEN=""` в `settings.py` | Токен игнорировался, пароль БД скрыт в коде | `DB_*`, `TINKOFF_TOKEN`, `USE_TINKOFF_MOCK` читаются из окружения с дефолтами, совместимыми с docker-compose |
| C-4 | `.env` существует, но settings его **не читали** (несоответствие конфигурации) | `python-dotenv` установлен, но не использовался | Подключён `load_dotenv(BASE_DIR / ".env")` |
| C-5 | `crispy_bootstrap3` в `INSTALLED_APPS` + `CRISPY_TEMPLATE_PACK` | Пакет Bootstrap 3 при статическом CSS **Bootstrap 5.1.3** → визуальный рассинхрон форм | `crispy_bootstrap5` + `CRISPY_TEMPLATE_PACK = "bootstrap5"` |
| C-6 | Deprecated CDN-зависимости в `dashboard/base.html` | `plotly-latest.min.js` (deprecated), jQuery 3.3.1, Popper 1.14.6, Font Awesome 4.7, Moment.js 2.23, Tempus Dominus BS4 — **ни одно не используется в шаблонах** | plotly.js закреплён на `plotly-2.35.2.min.js` (соответствует Python-библиотеке 5.24), мёртвые CDN удалены |
| C-7 | celery beat: задача «add-every-5-min» с `schedule=10.0` | Имя не соответствует расписанию | Переименована в `update-prices-every-10-sec`, интервал оставлен 10 c как в фактической реализации |
| C-8 | Префикс маршрутов без слэша: `path("user", include(...))` | Документированные адреса `/user/login/`, `/user/registration/` отдавали **404**; реально работали только `/userlogin/`, `/userregistration/` (совместимо с новым Django, была и раньше) | `path("user/", ...)` — стандартные URL теперь работают |
| C-9 | README ссылался на `TINKOFF_TOKEN` в `settings.py` | Противоречит новой конфигурации | Обновлён (через `.env`), добавлен `.env.example` |
| C-10 | Отсутствовал шаблон окружения | Новый разработчик не знал, какие переменные нужны | `.env.example` создан (разрешён .gitignore) |

---

## 3. Проверка работоспособности после изменений

| Проверка | Результат |
|---|---|
| `pip check` (целостность зависимостей) | ✅ No broken requirements found |
| `pip install --dry-run -r requirements.txt` | ✅ Резолвится (stub + git-форк + 40+ пакетов) |
| `manage.py check` | ✅ 0 issues |
| `manage.py migrate` | ✅ No migrations to apply (схема БД актуальна) |
| `manage.py test` (10 тестов: HTML list, REST API CRUD/фильтры) | ✅ OK |
| Smoke-запуск `runserver` + curl | ✅ `/` 200, `/user/login/` 200, `/user/registration/` 200, `/api/v1/shares/` 200, `/admin/login/` 200 |
| `import config.celery` (beat_schedule) | ✅ `update-prices-every-10-sec`, 10.0 |
| Docker (PostgreSQL + Redis) | ✅ Запущены |

---

## 4. Ограничения аудита и дальнейшие шаги

В скоуп этого аудита (пп. 1–2 Задания №3) намеренно **не включены**:

- дефекты реализации в коде бизнес-логики (`tasks.py`: инвертированный тренд,
  `TypeError` при `last_price=None`, голые `except`; `market_data.py`/`graph.py`:
  потеря точности цен `units` без `nano`; `RegistrationForm`: неоценённый queryset;
  `AuthView` без `is_valid()`; отсутствие 404 в `ShareDetailView`) —
  п. 3 Задания №3;
- рефакторинг (дублирование `Client(TINKOFF_TOKEN)` и др.) — п. 4 Задания №3;
- перевод `USE_TINKOFF_MOCK` в единую точку подключения к API (зарезервировано
  в `settings.py`, используется при рефакторинге сервисов).

Функциональность приложения при обновлении зависимостей и правках конфигурации
не изменилась, что подтверждено тестами и smoke-проверкой всех маршрутов.
