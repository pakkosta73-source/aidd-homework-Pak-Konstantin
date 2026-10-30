from config.celery import app
from dashboard.models import Share
from dashboard.services.market_data import get_last_data
from config.settings import logger


@app.task
def update_last_price():
    shares = Share.objects.all()

    for share in shares:
        try:
            [last_price, datetime] = get_last_data(share)

            if share.last_price is None:
                is_trend_high = True
            elif share.last_price < last_price:
                is_trend_high = True
            elif share.last_price > last_price:
                is_trend_high = False
            else:
                is_trend_high = share.is_trend_high if share.is_trend_high is not None else True

            Share.objects.filter(id=share.id).update(
                last_price=last_price, is_trend_high=is_trend_high
            )
        except TypeError as e:
            logger.error(f"TypeError updating price for share {share.id}: {e}")
        except ValueError as e:
            logger.error(f"ValueError getting data for share {share.id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating share {share.id}: {e}")
