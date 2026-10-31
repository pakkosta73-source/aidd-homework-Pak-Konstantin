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

## 4. Ошибки реализации и проектирования (Задание №3, п. 3 — исправлено)

| № | Дефект | Файл | Решение |
|---|---|---|---|
| F-1 | Потеря точности цен: учитывались только `price.units`, `nano` игнорировался → цена округлялась до целых рублей (для акций дешевле рубля — до нуля), тренд почти не менялся | `market_data.py`, `graph.py` | Добавлена `quotation_to_float()` (units + nano, корректный знак); используется в цене и на графике |
| F-2 | Инвертированная логика тренда: при росте цены записывался `is_trend_high=False`, при падении — `True` | `tasks.py` | Логика исправлена по BP-9: рост → `True`, падение → `False` |
| F-3 | `TypeError` при первом обновлении (`last_price=None`); голый `except` молча ставил `is_trend_high=True` | `tasks.py` | Тренд считается только при наличии прошлой цены; иначе `None` («не определён») |
| F-4 | Голые `except Exception` без контекста: реальная ошибка одного тикера прерывала обработку всех остальных и сообщения не содержали ни id, ни трейсбека | `tasks.py` | `logger.exception()` с id/тикером; сбой одной акции не прерывает цикл (`continue`) |
| F-5 | `Share.objects.get(id=pk)` при несуществующем pk → 500 | `views.py` | `get_object_or_404(Share, id=pk)` → 404 |
| F-6 | Сбой Tinkoff API при открытии карточки акции → 500 всей страницы | `views.py` | `get_graph()` обёрнут в try/except: страница открывается без графика, ошибка логируется |
| F-7 | `ShareModelForm(fields="__all__")`: пользователь мог подменить `uid`, `last_price`, `is_trend_high`, `updated_at` | `dashboard/forms.py` | Явный список полей: `figi, isin, name, ticker, currency` |
| F-8 | `AuthView.post` брал данные из `form.data` без `form.is_valid()` → `KeyError` при отсутствии поля POST | `user/views.py` | Валидация формы + `form.cleaned_data` |
| F-9 | Case-sensitivity email: вход приводит email к нижнему регистру, а регистрация — нет; пользователь, зарегистрировавшийся с заглавной буквы, не мог войти | `user/forms.py` | Email нормализуется к нижнему регистру при регистрации и в проверке дубликата (`email__iexact`) |
| F-10 | Ошибки регистрации доставались хрупко: `form.errors["__all__"].data[0].message` → `KeyError` при ошибке уровня поля (некорректный формат e-mail давал 500) | `user/views.py` | Сначала `non_field_errors()`, затем ошибки полей |
| F-11 | Проверка существования email через `if user:` на QuerySet — работает лишь за счёт неочевидного `QuerySet.__bool__` | `user/forms.py` | Явный `User.objects.filter(...).exists()`; сообщение сохранено |

**Примечание:** заявленный в предыдущем анализе дефект «регистрация всегда падает
из-за всегда-истинного queryset» не подтвердился: `if user:` на пустом QuerySet
корректно даёт `False`, что зафиксировано тестом
`test_registration_duplicate_email_rejected`. Проблема была в читаемости (F-11),
а не в неработоспособности.

### Тесты на исправленные дефекты (защита от регрессий)

- `dashboard/test_core.py` (9 тестов):
  - `UpdateLastPriceTests` — первое обновление (тренд `None`, не `True`), рост →
    `True` / падение → `False` (BP-9), сбой API по одной акции не рушит задачу
    и не портит данные остальных;
  - `ShareDetailViewTests` — 404 при несуществующем pk, рендер графика,
    страница без 500 при недоступном Tinkoff;
  - `ShareModelFormTests` — служебные поля не попадают в форму, подмена
    `last_price` через POST не работает.
- `user/tests.py` (8 тестов): успешная регистрация + автологин, нормализация
  email к нижнему регистру, отклонение дубликата e-mail, несовпадение паролей,
  вход (успешный, case-insensitive, неверный пароль), отсутствие поля POST
  не роняет сервер (устранён KeyError из F-8).

## 5. Сводная проверка работоспособности после всех изменений

| Проверка | Результат |
|---|---|
| `manage.py test` — все 27 тестов (10 исходных + 17 новых) | ✅ OK |
| `pip check` / `manage.py check` | ✅ 0 issues |
| Smoke-запуск runserver (`/`, `/user/login/`, `/user/registration/`, `/api/v1/shares/`, `/admin/login/`) | ✅ 200 |
| Docker (PostgreSQL + Redis) | ✅ Запущены |

## 6. Рефакторинг (Задание №3, п. 4 — выполнено)

| № | Проблема | Файлы | Решение |
|---|---|---|---|
| R-1 | Дублирование подключения к API: `Client(TINKOFF_TOKEN)` открывался в 3 местах (`market_data.py`, `graph.py`, `add_shares.py`) | все сервисы | Новый `dashboard/services/tinkoff_client.py`: единый контекстный менеджер `tinkoff_client()`; место для будущих ретраев/заглушек |
| R-2 | `update_last_price`: N запросов к API по одной акции (новый gRPC-клиент на каждую итерацию) + N отдельных UPDATE — весь каталог переписывался каждые 10 c | `tasks.py`, `market_data.py` | Батч: один `get_last_prices(figi=[...])` на весь каталог + один `bulk_update`; сбой пачки не портит данные |
| R-3 | Неиспользуемое значение `update_time` возвращалось из `get_last_data`, но нигде не сохранялось | `market_data.py`, `tasks.py` | Убрано; `fetch_last_prices(figis) → {figi: price}` |
| R-4 | График: plotly инлайнил ~3 МБ JS в каждую страницу (`include_plotlyjs=True` по умолчанию) при уже подключённом CDN (fix C-6) | `graph.py` | `include_plotlyjs=False`; страница отдаёт div с данными |
| R-5 | `add_shares`: `get_or_create` по **всем** полям сразу — при изменении данных существующей акции (переименование в API) попытка создания дубля по unique-figi → IntegrityError ломала импорт | `add_shares.py` | `get_or_create(figi, defaults={...})`; сводка «загружено/новых» в stdout |
| R-6 | Дублирование атрибутов виджетов `"form-control my-3 p-4"` и нормализации email в forms/views | `user/forms.py`, `user/views.py` | Константа `COMMON_INPUT_ATTRS`; email нормализуется в `clean_email` форм (views стало проще); дубли сообщений убраны |
| R-7 | Копипаст-docstring «Удаление задачи» у ShareDeleteView | `dashboard/views.py` | Исправлено на «Удаление инструмента» |
| R-8 | Код отформатирован по конвенции проекта (best-practices skill: Black + isort) | все изменённые файлы | `isort --profile black` + `black` |

Пропущено сознательно (за рамками выполняемого объёма): кеширование графика
180 дней, rate limiting API, реальная реализация `USE_TINKOFF_MOCK` для
сервисов (требуется фейковый источник данных).

## 7. Итоговая проверка работоспособности после рефакторинга

| Проверка | Результат |
|---|---|
| `manage.py test` — 31 тест (10 исходных + 21 добавленных) | ✅ OK |
| Тесты нового поведения: батч-обновление (R-2), устойчивость `add_shares` (R-5), сохранение данных при сбое API | ✅ покр |
| `pip check` / `manage.py check` | ✅ 0 issues |
| Smoke-запуск runserver (`/`, `/user/login/`, `/api/v1/shares/`) | ✅ 200 |
| Docker (PostgreSQL + Redis) | ✅ Запущены |

## 8. Ограничения аудита и дальнейшие шаги

- Из-за объёма сознательно не тронуто (целесообразно при появлении нагрузки /
  в рамках Задания №4): кеширование графика 180 дней, rate limiting API,
  реальная реализация `USE_TINKOFF_MOCK` для сервисов (требуется фейковый
  источник данных).
- Парольные валидаторы (`AUTH_PASSWORD_VALIDATORS`) на регистрации не
  включались: по восстановленным BP-6 требуется лишь совпадение паролей и
  уникальность email (включение валидаторов изменило бы функциональные
  требования).
