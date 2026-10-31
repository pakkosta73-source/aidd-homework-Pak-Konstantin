from django.core.management.base import BaseCommand

from dashboard.models import Share
from dashboard.services.tinkoff_client import tinkoff_client


class Command(BaseCommand):
    help = "Импортирует каталог акций из Tinkoff Invest API (get_or_create по figi)"

    def handle(self, *args, **options):
        created_count = 0
        with tinkoff_client() as client:
            instruments = client.instruments.shares().instruments

            for instrument in instruments:
                # Раньше lookup шёл по всем полям сразу: при изменившемся
                # названии/валюте существующей акции get_or_create пытался
                # создать дубликат по figi и падал IntegrityError.
                _, created = Share.objects.get_or_create(
                    figi=instrument.figi,
                    defaults={
                        "name": instrument.name,
                        "isin": instrument.isin,
                        "ticker": instrument.ticker,
                        "currency": instrument.currency,
                        "uid": instrument.uid,
                    },
                )
                created_count += int(created)

        self.stdout.write(
            f"Каталог загружен: {len(instruments)} акций, из них новых: {created_count}"
        )
