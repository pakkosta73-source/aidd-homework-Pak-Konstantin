# investing

# PostgreSQL (Docker)
docker-compose -f docker-compose.yml up

# Tinkoff Invest API
# TINKOFF_TOKEN задаётся в файле .env (шаблон — .env.example); настройки читаются через python-dotenv
#
# Режим заглушки для локальной разработки (без токена и сети):
#   USE_TINKOFF_MOCK=True  в .env
# При пустом TINKOFF_TOKEN заглушка включается автоматически.
# Заглушка отдаёт синтетические цены (random walk), историю для графика
# и каталог из 5 акций для `python manage.py add_shares`.

# Первоначальная загрузка списка акций
python manage.py add_shares

# Celery Beat
celery -A config beat

# Celery Worker
celery -A config worker -l info

# Celery Worker для Windows (Eventlet)
pip install eventlet cryptography
celery -A config worker -l info -P eventlet

# API
# /api/v1/shares — работа с акциями
