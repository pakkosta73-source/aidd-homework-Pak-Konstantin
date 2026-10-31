from config.celery import app
from config.settings import logger
from dashboard.models import Notification, Share, WatchlistEntry
from dashboard.services.market_data import fetch_last_prices


@app.task
def update_last_price():
    """Обновляет последнюю цену и тренд всех акций за один проход.

    Отличия от исходной реализации:
    - цены запрашиваются одним батч-запросом, а не N запросами
      с новым gRPC-клиентом на каждую акцию;
    - записи обновляются одним `bulk_update`, а не N отдельными UPDATE;
    - сбой при получении пачки не ломает данные (старые цены сохраняются).
    """
    shares = list(Share.objects.all())
    if not shares:
        return

    try:
        prices = fetch_last_prices([share.figi for share in shares])
    except Exception:
        logger.exception("Failed to fetch prices from Tinkoff API")
        return

    to_update = []
    for share in shares:
        price = prices.get(share.figi)
        if price is None:
            continue

        if share.last_price is not None:
            # Цена выросла → True (рост), упала → False (падение).
            # Исходный код содержал инвертированную логику.
            is_trend_high = price > share.last_price
        else:
            # Прежняя цена неизвестна (первое обновление): тренд не определён.
            is_trend_high = None

        share.last_price = price
        share.is_trend_high = is_trend_high
        to_update.append(share)

    if to_update:
        Share.objects.bulk_update(to_update, ["last_price", "is_trend_high"])
        logger.info(f"Prices updated for {len(to_update)} shares")

    missing = len(shares) - len(to_update)
    if missing:
        logger.warning(f"{missing} shares skipped: no price returned")

    _check_watchlist_conditions()


def _check_watchlist_conditions():
    """Проверяет условия наблюдений после обновления цен.

    - проверяются только записи, по которым уведомление ещё не отправлялось
      (notified=False) — это исключает дублирование уведомления об одном
      и том же событии;
    - повторное уведомление возможно только после ручного перевзвода
      (кнопка «сбросить» на странице наблюдений);
    - акция без текущей цены (None) не проверяется.
    """
    shares = {share.id: share for share in Share.objects.exclude(last_price=None)}

    triggered = []
    entries = WatchlistEntry.objects.filter(notified=False).select_related(
        "user", "share"
    )
    for entry in entries:
        share = shares.get(entry.share_id)
        if share is None:
            continue

        if entry.condition == WatchlistEntry.CONDITION_ABOVE:
            fired = share.last_price >= entry.target_price
        else:
            fired = share.last_price <= entry.target_price

        if fired:
            triggered.append(
                (
                    entry,
                    Notification(
                        user=entry.user,
                        share=share,
                        message=(
                            f"{share.name} ({share.ticker}): цена "
                            f"{share.last_price:.2f} {share.currency} "
                            f"достигла уровня {entry.target_price:.2f} "
                            f"({'выше' if entry.condition == WatchlistEntry.CONDITION_ABOVE else 'ниже'} цели)"
                        ),
                    ),
                )
            )

    if not triggered:
        return

    # Помечаем сработавшие записи — до ручного сброса уведомления повторятся не будут.
    WatchlistEntry.objects.filter(pk__in=[entry.pk for entry, _ in triggered]).update(
        notified=True
    )
    Notification.objects.bulk_create([notification for _, notification in triggered])
    logger.info(
        f"Watchlist notifications created: {len(triggered)} "
        f"for users {sorted({entry.user_id for entry, _ in triggered})}"
    )
