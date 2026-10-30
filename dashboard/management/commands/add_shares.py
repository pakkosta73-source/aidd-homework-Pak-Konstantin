from django.core.management.base import BaseCommand

from dashboard.models import Share
from dashboard.services.tinkoff_client import get_client


class Command(BaseCommand):
    help = "Load shares catalog from Tinkoff API into the database"

    def handle(self, *args, **options):
        with get_client() as client:
            shares = client.instruments.shares()
            for share in shares.instruments:
                Share.objects.get_or_create(
                    figi=share.figi,
                    defaults={
                        "name": share.name,
                        "isin": share.isin,
                        "ticker": share.ticker,
                        "currency": share.currency,
                        "uid": share.uid,
                    },
                )
            self.stdout.write(
                self.style.SUCCESS(f"Loaded {len(shares.instruments)} shares")
            )


