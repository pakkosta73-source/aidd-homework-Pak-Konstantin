from config.settings import logger

from .tinkoff_client import get_client


def get_last_data(share):
    """Получить последнюю цену акции через Tinkoff API."""
    with get_client() as client:
        resp = client.market_data.get_last_prices(figi=[share.figi])
        candle = resp.last_prices.pop()
        logger.info(f"Get last data for share with id {share.id}")
        return candle.price.units, candle.time
