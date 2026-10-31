"""Тесты режима заглушки Tinkoff API (USE_TINKOFF_MOCK)."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase

from dashboard.models import Share
from dashboard.services.market_data import fetch_last_prices, quotation_to_float
from dashboard.services.tinkoff_client import (
    MockClient,
    MockQuotation,
    _base_price,
    _quotation,
    tinkoff_client,
)
from dashboard.services.tinkoff_client import (
    USE_TINKOFF_MOCK,  # noqa: F401 — monkeypatch-цель для patch()
)
from tinkoff.invest.utils import now


class MockClientTests(TestCase):
    """MockClient имитирует вызовы, используемые в проекте."""

    def test_last_prices_all_figis_present(self):
        client = MockClient()
        figis = ["FIGI_ONE", "FIGI_TWO"]
        response = client.market_data.get_last_prices(figi=figis)
        returned = {item.figi for item in response.last_prices}
        self.assertEqual(returned, set(figis))
        for item in response.last_prices:
            price = quotation_to_float(item.price)
            self.assertGreater(price, 0)

    def test_price_changes_between_calls(self):
        """Заглушка должна «шуметь»: цены меняются от запроса к запросу, иначе тренд не покажется."""
        client = MockClient()
        first = quotation_to_float(
            client.market_data.get_last_prices(figi=["FIGI"]).last_prices[0].price
        )
        changed = any(
            quotation_to_float(item.price) != first
            for item in client.market_data.get_last_prices(figi=["FIGI"] * 20).last_prices
        )
        self.assertTrue(changed)

    def test_prices_stay_near_base(self):
        client = MockClient()
        base = _base_price("FIGI")
        for _ in range(50):
            price = quotation_to_float(
                client.market_data.get_last_prices(figi=["FIGI"]).last_prices[0].price
            )
            self.assertTrue(base * 0.79 <= price <= base * 1.21, (price, base))

    def test_candles_deterministic_and_complete(self):
        """История за 180 дней: детерминирована и покрывает весь период."""
        client = MockClient()
        from_ = now() - timedelta(days=180)
        first = [
            (c.time.date(), quotation_to_float(c.close))
            for c in client.get_all_candles(figi="FIGI", from_=from_)
        ]
        second = [
            (c.time.date(), quotation_to_float(c.close))
            for c in client.get_all_candles(figi="FIGI", from_=from_)
        ]
        self.assertEqual(first, second)
        self.assertEqual(len(first), 181)
        self.assertTrue(all(low > 0 for _, low in first))
        # цены от рассчётной базы не убегают бесконечно
        base = _base_price("FIGI")
        for _, close in first:
            self.assertLess(close, base * 10)

    def test_quotation_round_trip(self):
        q = _quotation(150.25)
        self.assertEqual(quotation_to_float(q), 150.25)

    def test_quotation_no_negative_nano(self):
        q = _quotation(0.5)
        self.assertEqual(q.units, 0)
        self.assertEqual(quotation_to_float(q), 0.5)


class TinkoffClientMockSwitchTests(TestCase):
    """Переключение real/ mock в контекст-менеджере tinkoff_client()."""

    def test_mock_mode_returns_mock_client(self):
        with patch("dashboard.services.tinkoff_client.USE_TINKOFF_MOCK", True):
            with tinkoff_client() as client:
                self.assertTrue(isinstance(client, MockClient))

    def test_real_mode_without_token_is_not_mock(self):
        """С реальным токеном и выключенным mock отдаётся настоящий Client."""
        with patch("dashboard.services.tinkoff_client.USE_TINKOFF_MOCK", False), patch(
            "dashboard.services.tinkoff_client.TINKOFF_TOKEN", "real-token"
        ):
            with tinkoff_client() as client:
                self.assertNotIsInstance(client, MockClient)


class MockCatalogTests(TestCase):
    """management-команда add_shares работает на заглушке без токена."""

    def test_add_shares_with_mock_catalog(self):
        from django.core.management import call_command

        with patch("dashboard.services.tinkoff_client.USE_TINKOFF_MOCK", True):
            call_command("add_shares")
        self.assertGreaterEqual(Share.objects.count(), 5)
        self.assertTrue(Share.objects.filter(ticker="AAPL").exists())

    def test_quotation_to_float_keeps_fractional_price(self):
        """units-only ломал акции дешевле 1.0 — заглушка такое же поведение ловит."""
        self.assertEqual(quotation_to_float(MockQuotation(0, 500_000_000)), 0.5)
