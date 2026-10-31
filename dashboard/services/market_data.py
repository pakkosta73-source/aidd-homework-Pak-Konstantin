"""Получение рыночных данных: последние цены акций через Tinkoff API."""

from tinkoff.invest import Quotation

from dashboard.services.tinkoff_client import tinkoff_client


def quotation_to_float(quotation: Quotation) -> float:
    """Преобразует Quotation (units + nano) в float без потери копеек.

    Раньше в расчёте использовались только units — цена округлялась до целых
    рублей (а для акций дешевле рубля — вообще до нуля), что искажало и тренд.
    Если units отрицательный, nano добавляется со знаком минус (по контракту
    Tinkoff: nano всегда неотрицателен).
    """
    if quotation.units < 0:
        return float(quotation.units - quotation.nano / 1_000_000_000)
    return float(quotation.units + quotation.nano / 1_000_000_000)


def fetch_last_prices(figis: list[str]) -> dict[str, float]:
    """Последние цены по списку FIGI.

    Один запрос на весь список вместо N запросов по одной акции.
    Возвращает {figi: price}; инструменты без данных в ответе отсутствуют.
    """
    if not figis:
        return {}
    with tinkoff_client() as client:
        response = client.market_data.get_last_prices(figi=figis)
    return {item.figi: quotation_to_float(item.price) for item in response.last_prices}
