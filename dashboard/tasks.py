from config.celery import app
from config.settings import logger
from dashboard.models import Notification, Share, WatchlistEntry
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


def _check_watchlist_conditions():
    """Проверить условия списка наблюдения и создать уведомления."""
    entries_to_update = []
    notifications_to_create = []

    for entry in WatchlistEntry.objects.filter(notified=False).select_related("share"):
        current_price = entry.share.last_price
        if current_price is None:
            continue

        condition_met = False
        if entry.condition == WatchlistEntry.CONDITION_ABOVE and current_price >= entry.target_price:
            condition_met = True
        elif entry.condition == WatchlistEntry.CONDITION_BELOW and current_price <= entry.target_price:
            condition_met = True

        if condition_met:
            entry.notified = True
            entries_to_update.append(entry)
            notifications_to_create.append(
                Notification(
                    user=entry.user,
                    share=entry.share,
                    message=(
                        f"{entry.share.ticker} достигла целевой цены "
                        f"{entry.target_price:.2f} (текущая: {current_price:.2f})"
                    ),
                )
            )

    if entries_to_update:
        WatchlistEntry.objects.bulk_update(entries_to_update, ["notified"])
        logger.info(f"Watchlist: {len(entries_to_update)} entries notified")

    if notifications_to_create:
        Notification.objects.bulk_create(notifications_to_create)
        logger.info(f"Watchlist: {len(notifications_to_create)} notifications created")


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

    # Проверить условия списка наблюдения после обновления цен
    try:
        _check_watchlist_conditions()
    except Exception as e:
        logger.error(f"Error checking watchlist conditions: {e}")
