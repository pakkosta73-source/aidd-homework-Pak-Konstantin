"""Единая точка подключения к Tinkoff Invest API.

Ранее `Client(TINKOFF_TOKEN)` открывался отдельно в трёх местах:
market_data.py, graph.py и management-команде add_shares. Теперь все
интеграции используют один контекстный менеджер, что упрощает будущую
поддержку (логирование, ретраи, тестовые заглушки через USE_TINKOFF_MOCK).

Режим заглушки (USE_TINKOFF_MOCK=True, либо автоматически при пустом
TINKOFF_TOKEN): локальная разработка без токена и без сети. MockClient
имитирует сетевые ответы API и выдаёт правдоподобные, но синтетические
данные — цены слегка «гуляют» от запроса к запросу, поэтому график
и тренд на списке выглядят живыми.
"""

from __future__ import annotations

import hashlib
import random
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from tinkoff.invest import CandleInterval, Client

from config.settings import TINKOFF_TOKEN, USE_TINKOFF_MOCK, logger


# ────────────────────────────── Заглушка ──────────────────────────────


@dataclass
class MockQuotation:
    """Аналог tinkoff.invest Quotation (units + nano)."""

    units: int
    nano: int


@dataclass
class MockLastPrice:
    figi: str
    price: MockQuotation


@dataclass
class MockLastPricesResponse:
    last_prices: list = field(default_factory=list)


@dataclass
class MockCandle:
    time: datetime
    close: MockQuotation


@dataclass
class MockInstrument:
    figi: str
    name: str
    isin: str
    ticker: str
    currency: str
    uid: str


def _quotation(price: float) -> MockQuotation:
    """float → Quotation (units + nano), как в контракте Tinkoff API."""
    units = int(price)
    nano = round((price - units) * 1_000_000_000)
    if nano >= 1_000_000_000:  # страх от округлений float вверх
        units += 1
        nano -= 1_000_000_000
    return MockQuotation(units=units, nano=nano)


def _figi_seed(figi: str) -> int:
    """Стабильное (одно и то же для данного figi) псевдослучайное зерно."""
    return int(hashlib.sha1(figi.encode()).hexdigest()[:8], 16)


def _base_price(figi: str) -> float:
    """Стабильная «базовая» цена для figi: детерминирована по figi."""
    rng = random.Random(_figi_seed(figi))
    # правдоподобный диапазон акций: 3.50 … 2 500.00
    return round(3.5 + rng.random() ** 2 * 2496.5, 2)


class MockClient:
    """Имитация tinkoff.invest.Client.

    Поддерживает только те вызовы, которые реально используются
    в проекте: market_data.get_last_prices, get_all_candles,
    instruments.shares.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Текущее "живое" состояние цены (random walk), init — Base по figi
        self._prices: dict[str, float] = {}
        self.market_data = _MockMarketData(self)
        self.instruments = _MockInstruments()

    # ── внутренние ──

    def _next_price(self, figi: str) -> float:
        """Цена с лёгким шагом random walk (±0.5%) от базовой.

        Первую цену берём ровно базовой, чтобы тренд на первом обновлении
        был осмысленным, далее шаг двигает цену вокруг базовой.
        """
        base = _base_price(figi)
        with self._lock:
            price = self._prices.get(figi, base)
            price *= 1 + random.uniform(-0.005, 0.005)
            # не уводим цену слишком далеко от base
            price = min(max(price, base * 0.8), base * 1.2)
            self._prices[figi] = round(price, 2)
        return self._prices[figi]

    # ── публичный интерфейс, который реально вызывает код ──

    def get_last_prices(self, figi: list[str]) -> MockLastPricesResponse:
        """Одна пачка цен для всех figi, как в market_data.fetch_last_prices."""
        response = MockLastPricesResponse(
            last_prices=[MockLastPrice(figi=f, price=_quotation(self._next_price(f))) for f in figi]
        )
        return response

    def get_all_candles(
        self,
        *,
        figi: str,
        from_: datetime,
        interval: CandleInterval = CandleInterval.CANDLE_INTERVAL_DAY,
    ) -> list:
        """Детерминированная дневная история цен (для графика в graph.py).

        История фиксирована для конкретного figi (seed по figi), при этом
        завершающий день не обязан совпадать с текущей ценой из
        get_last_prices, как и в реальном мире (close vs last trade).
        """
        rng = random.Random(_figi_seed(figi))
        price = _base_price(figi)

        start = from_.astimezone(timezone.utc).date()
        today = datetime.now(timezone.utc).date()

        candles = []
        day = start
        while day <= today:
            price *= 1 + rng.uniform(-0.02, 0.02)
            price = min(max(price, 1.0), 5000.0)
            candles.append(
                MockCandle(
                    time=datetime(day.year, day.month, day.day, tzinfo=timezone.utc),
                    close=_quotation(round(price, 2)),
                )
            )
            day += timedelta(days=1)
        return candles


class _MockMarketData:
    def __init__(self, client: MockClient):
        self._client = client

    def get_last_prices(self, figi: list[str]) -> MockLastPricesResponse:
        return self._client.get_last_prices(figi)


class _MockInstruments:
    """Каталог акций для management-команды add_shares."""

    _catalog = [
        ("BBG000B9XRY4", "Apple Inc.", "US0378331005", "AAPL", "usd"),
        ("BBG000BPHFS9", "Microsoft Corp.", "US5949181045", "MSFT", "usd"),
        ("BBG004730N88", "Сбербанк", "RU0009029540", "SBER", "rub"),
        ("BBG0047315D7", "Газпром", "RU000A0JX0J4", "GAZP", "rub"),
        ("BBG00RNDS3H7", "Яндекс", "RU000A1ZX4W7", "YNDX", "rub"),
    ]

    def shares(self):
        instruments = [
            MockInstrument(
                figi=figi,
                name=name,
                isin=isin,
                ticker=ticker,
                currency=currency,
                uid=_uuid_from_figi(figi),
            )
            for figi, name, isin, ticker, currency in self._catalog
        ]
        return _MockSharesResponse(instruments)


@dataclass
class _MockSharesResponse:
    instruments: list


def _uuid_from_figi(figi: str) -> str:
    """Детерминированный UUID для стабильности каталога."""
    import uuid

    return str(uuid.UUID(hex=hashlib.md5(f"uid-{figi}".encode()).hexdigest()))


# ─────────────────────── Точка подключения ───────────────────────


@contextmanager
def tinkoff_client():
    """Открывает соединение с Tinkoff Invest API для блока кода.

    При USE_TINKOFF_MOCK=True (или при пустом TINKOFF_TOKEN локально)
    отдаёт MockClient — синтетические данные без сети и токена.
    """
    if USE_TINKOFF_MOCK:
        logger.info("Tinkoff API: режим заглушки (USE_TINKOFF_MOCK=True)")
        yield MockClient()
        return
    if not TINKOFF_TOKEN:
        logger.warning(
            "TINKOFF_TOKEN пуст — включаю заглушку с тестовыми данными. "
            "Задайте реальный токен в .env, чтобы получать рыночные данные."
        )
        yield MockClient()
        return
    with Client(TINKOFF_TOKEN) as client:
        yield client
