# Investing Demo — Best Practices

**Trigger:** Use this skill before making any changes to the Investing Demo project — it contains essential guidelines for working with secrets, forms, models, API, and Celery tasks.

## Рекомендации при работе с проектом

### Секреты и конфигурация
- Всегда используйте `.env` файл для секретов (`SECRET_KEY`, `TINKOFF_TOKEN`, пароли БД).
- Не коммитьте `config/settings.py` с реальными секретами.
- При деплое установите `DEBUG = False` и заполните `ALLOWED_HOSTS`.

### Работа с моделями
- При изменении модели `Share` не забывайте про миграции: `python manage.py makemigrations && python manage.py migrate`.
- Поля `last_price`, `is_trend_high`, `uid`, `figi` должны управляться автоматически — не давайте пользователю их редактировать.
- `ShareModelForm` должен использовать явный список полей, а не `fields = "__all__"`.

### REST API
- `ShareViewSet` открыт без аутентификации — учитывайте это при тестировании.
- При добавлении новых эндпоинтов не забудьте про `permission_classes`, если требуется авторизация.
- API использует `LimitOffsetPagination` с 100 записями по умолчанию.

### Celery и фоновые задачи
- Задача обновления цен запускается каждые 10 секунд — при отладке учитывайте частоту вызовов Tinkoff API.
- Перед запуском убедитесь, что `TINKOFF_TOKEN` установлен валидный.
- Celery worker и beat должны запускаться отдельно от Django-сервера.

### Формы и шаблоны
- **Критический фикс:** `RegistrationForm` не работает — queryset не оценён. Используйте `User.objects.filter(email=email).exists()` или `.first()`.
- При работе с формами убедитесь, что шаблоны содержат `{% csrf_token %}`.
- `AuthView` должен использовать `form.is_valid()` перед обращением к `form.data`.

### Тестирование
- Существующие тесты покрывают только API CRUD.
- При изменении бизнес-логики добавьте тесты для Celery-задач, сервисов и форм.
- Используйте фикстуры для мокирования Tinkoff API.

### Инфраструктура
- `docker-compose.yml` содержит только PostgreSQL и Redis — для полного запуска нужен сервис приложения.
- Запуск приложения:
  ```bash
  docker-compose up -d  # БД и Redis
  python manage.py migrate
  python manage.py add_shares  # Загрузка каталога
  python manage.py runserver
  ```
- Запуск Celery:
  ```bash
  celery -A config worker --loglevel=info
  celery -A config beat --loglevel=info
  ```

### Код-стайл
- Используйте Black для форматирования кода.
- Используйте isort для сортировки импортов.
- Следуйте существующим паттернам в коде — не вводите новые стили без необходимости.
