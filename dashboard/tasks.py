from config.celery import app
from config.settings import logger
from dashboard.models import Share
from dashboard.services.market_data import get_last_data


def _calculate_trend(share, last_price):
    """Определить тренд цены: True — рост, False — падение."""
    if share.last_price is None:
        return True
    if share.last_price < last_price:
        return True
    if share.last_price > last_price:
        return False
    return share.is_trend_high if share.is_trend_high is not None else True


@app.task
def update_last_price():
    """Периодически обновлять цены акций через Tinkoff API."""
    shares = Share.objects.all()
    updated = []

    for share in shares:
        try:
            last_price, _ = get_last_data(share)
            share.last_price = last_price
            share.is_trend_high = _calculate_trend(share, last_price)
            updated.append(share)
        except (TypeError, ValueError) as e:
            logger.error(f"Error updating price for share {share.id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating share {share.id}: {e}")

    if updated:
        Share.objects.bulk_update(updated, ["last_price", "is_trend_high"])
