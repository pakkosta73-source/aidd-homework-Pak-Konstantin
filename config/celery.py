import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "update-prices-every-10-sec": {
        "task": "dashboard.tasks.update_last_price",
        # Фактический интервал — 10 секунд (старое название «add-every-5-min»
        # не соответствовало расписанию — исправлено).
        "schedule": 10.0,
    },
}
