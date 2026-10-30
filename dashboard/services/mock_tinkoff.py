"""Заглушка Tinkoff Invest API для разработки и тестирования без реального подключения."""
from datetime import datetime, timedelta
from typing import Iterator

from tinkoff.invest import CandleInterval
from tinkoff.invest.utils import now


class MockInstrument:
    """Заглушка инструмента (акции)."""

    def __init__(self, figi, isin, name, ticker, currency, uid):
        self.figi = figi
        self.isin = isin
        self.name = name
        self.ticker = ticker
        self.currency = currency
        self.uid = uid


class MockSharesResponse:
    """Ответ на instruments.shares()."""

    def __init__(self, instruments):
        self.instruments = instruments


class MockCandle:
    """Свеча для графика."""

    def __init__(self, time, close_units):
        self.time = time
        self.close = type('obj', (object,), {'units': close_units})()


class MockPrice:
    """Последняя цена."""

    def __init__(self, price_units, time):
        self.price = type('obj', (object,), {'units': price_units})()
        self.time = time


class MockLastPricesResponse:
    """Ответ на market_data.get_last_prices()."""

    def __init__(self, prices):
        self.last_prices = prices


# Тестовые данные — популярные акции
MOCK_SHARES = [
    MockInstrument(
        figi="a9786a00-711d-44b0-b0d8-6bb3f088d674",
        isin="RU0009029710",
        name="Сбербанк",
        ticker="SBER",
        currency="RUB",
        uid="b45d3dcf-a1b2-4c3d-8e4f-5a6b7c8d9e0f",
    ),
    MockInstrument(
        figi="30d9d33b-f2cd-4998-8aa1-8695e18fe016",
        isin="RU0001010068",
        name="Газпром",
        ticker="GAZP",
        currency="RUB",
        uid="c56e4def-b2c3-5d4e-9f5a-6b7c8d9e0f1a",
    ),
    MockInstrument(
        figi="5d7720b6-7b29-4e6e-9c3d-4e5f6a7b8c9d",
        isin="RU0009130120",
        name="Лукойл",
        ticker="LKOH",
        currency="RUB",
        uid="d67f5efa-c3d4-6e5f-0a6b-7c8d9e0f1a2b",
    ),
    MockInstrument(
        figi="6e8831c7-8c3a-5f7e-ad4e-5f6a7b8c9d0e",
        isin="RU0009029664",
        name="Яндекс",
        ticker="YNDX",
        currency="RUB",
        uid="e78a6fab-d4e5-7f6a-1b7c-8d9e0f1a2b3c",
    ),
    MockInstrument(
        figi="7f9942d8-9d4b-6a8f-be5f-6a7b8c9d0e1f",
        isin="RU000A0JRPE8",
        name="Норникель",
        ticker="GMKN",
        currency="RUB",
        uid="f89b7abc-e5f6-8a7b-2c8d-9e0f1a2b3c4d",
    ),
    MockInstrument(
        figi="8a0053e0-ae5c-7b9a-cf6a-7b8c9d0e1f2a",
        isin="RU0009069007",
        name="Роснефть",
        ticker="ROSN",
        currency="RUB",
        uid="a90c8bcd-f6a7-9b8c-3d9e-0f1a2b3c4d5e",
    ),
    MockInstrument(
        figi="9b1164f1-bf6d-8c0b-da7b-8c9d0e1f2a3b",
        isin="RU0001316360",
        name="Татнефть",
        ticker="TATN",
        currency="RUB",
        uid="b01d9cde-a7b8-0c9d-4e0f-1a2b3c4d5e6f",
    ),
    MockInstrument(
        figi="0c2275a2-ca7e-9d1c-eb8c-9d0e1f2a3b4c",
        isin="RU0009105101",
        name="МТС",
        ticker="MTSS",
        currency="RUB",
        uid="c12e0def-b8c9-1d0e-5f1a-2b3c4d5e6f7a",
    ),
]

# Цены для каждой акции (по figi)
# Включает figi из MOCK_SHARES и реальные figi из Tinkoff API (BBG-формат)
MOCK_PRICES = {
    # MOCK figi (тестовые данные)
    "5d7720b6-7b29-4e6e-9c3d-4e5f6a7b8c9d": 7450.50,  # LKOH
    "30d9d33b-f2cd-4998-8aa1-8695e18fe016": 165.25,   # GAZP
    "a9786a00-711d-44b0-b0d8-6bb3f088d674": 285.40,   # SBER
    "6e8831c7-8c3a-5f7e-ad4e-5f6a7b8c9d0e": 3250.00,  # YNDX
    "7f9942d8-9d4b-6a8f-be5f-6a7b8c9d0e1f": 16800.75, # GMKN
    "8a0053e0-ae5c-7b9a-cf6a-7b8c9d0e1f2a": 545.30,   # ROSN
    "9b1164f1-bf6d-8c0b-da7b-8c9d0e1f2a3b": 5890.20,  # TATN
    "0c2275a2-ca7e-9d1c-eb8c-9d0e1f2a3b4c": 352.15,   # MTSS
    # Реальные figi из Tinkoff API (BBG-формат)
    "BBG000B9XRY4": 178.50,    # AAPL
    "BBG004731N89": 285.40,    # SBER
}


class MockInstruments:
    """Заглушка instruments-сервиса."""

    def shares(self):
        return MockSharesResponse(MOCK_SHARES)


class MockMarketData:
    """Заглушка market_data-сервиса."""

    def get_last_prices(self, figi):
        prices = []
        for f in figi:
            price_units = MOCK_PRICES.get(f, 1000.0)
            prices.append(MockPrice(price_units, now()))
        return MockLastPricesResponse(prices)


class MockTinkoffClient:
    """Заглушка Tinkoff Invest клиента.

    Имитирует интерфейс реального клиента для разработки без подключения к API.
    """

    def __init__(self):
        self.instruments = MockInstruments()
        self.market_data = MockMarketData()

    def get_all_candles(self, figi, from_, interval):
        """Сгенерировать случайные свечи для графика."""
        candles = []
        base_price = MOCK_PRICES.get(figi, 1000.0)
        days = (now() - from_).days
        current_price = base_price * 0.8  # начинаем с 80% от текущей цены

        for day in range(days):
            time = from_ + timedelta(days=day)
            # Генерируем цену с небольшим случайным изменением
            change = (day % 7 - 3) * (base_price * 0.01)  # колебание ±3%
            current_price = current_price + change
            # Убедимся, что последняя свеча близка к текущей цене
            if day == days - 1:
                current_price = base_price
            candles.append(MockCandle(time, current_price))

        return iter(candles)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
