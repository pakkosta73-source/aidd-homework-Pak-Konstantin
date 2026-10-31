"""Тесты исправленных дефектов: Celery-задача цен, страница акции, форма инструмента."""

from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from dashboard.forms import ShareModelForm
from dashboard.models import Share
from dashboard.tasks import update_last_price


def _make_share(**kwargs):
    fields = dict(
        figi="BBG000B9XRY4",
        isin="US0378331005",
        name="Apple",
        ticker="AAPL",
        currency="usd",
        uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
    )
    fields.update(kwargs)
    return Share.objects.create(**fields)


class UpdateLastPriceTests(TestCase):
    """Дефекты задачи update_last_price: инверсия тренда и TypeError при None."""

    def _patch_service(self, prices: dict):
        return patch("dashboard.tasks.fetch_last_prices", return_value=prices)

    def test_first_update_trend_not_determined(self):
        """Первое обновление: прошлой цены нет, тренд должен быть None (не True)."""
        share = _make_share(last_price=None, is_trend_high=None)
        with self._patch_service({share.figi: 150.25}):
            update_last_price()
        share.refresh_from_db()
        self.assertEqual(share.last_price, 150.25)
        self.assertIsNone(share.is_trend_high)

    def test_price_grows_marks_trend_high(self):
        """Цена выросла → is_trend_high=True (исходный код ставил False)."""
        share = _make_share(last_price=100.0, is_trend_high=False)
        with self._patch_service({share.figi: 101.5}):
            update_last_price()
        share.refresh_from_db()
        self.assertTrue(share.is_trend_high)

    def test_price_falls_marks_trend_low(self):
        """Цена упала → is_trend_high=False (исходный код ставил True)."""
        share = _make_share(last_price=100.0, is_trend_high=True)
        with self._patch_service({share.figi: 99.5}):
            update_last_price()
        share.refresh_from_db()
        self.assertFalse(share.is_trend_high)

    def test_prices_updated_in_bulk(self):
        """Пакетный режим: несколько акций обновляются за один проход."""
        first = _make_share(last_price=10.0, is_trend_high=None)
        second = _make_share(
            figi="BBG000B9XRY5",
            isin="US0378331004",
            ticker="MSFT",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e39",
            last_price=50.0,
            is_trend_high=None,
        )
        with self._patch_service({first.figi: 11.0, second.figi: 49.0}):
            update_last_price()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.last_price, 11.0)
        self.assertTrue(first.is_trend_high)
        self.assertEqual(second.last_price, 49.0)
        self.assertFalse(second.is_trend_high)

    def test_share_without_price_keeps_previous_data(self):
        """Акция, по которой API не вернул цену, остаётся без изменений."""
        tracked = _make_share(
            figi="BBG000B9XRY5",
            isin="US0378331004",
            ticker="MSFT",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e39",
            last_price=50.0,
            is_trend_high=True,
        )
        unknown = _make_share(
            figi="BBG000B9XRY6",
            isin="US0378331006",
            name="Tesco",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e40",
            last_price=None,
            is_trend_high=None,
        )

        with self._patch_service({tracked.figi: 51.0}):
            update_last_price()  # не должно бросать исключений

        tracked.refresh_from_db()
        unknown.refresh_from_db()
        self.assertEqual(tracked.last_price, 51.0)
        self.assertTrue(tracked.is_trend_high)
        # unknown: цена от API не пришла — данные по акции не изменились
        self.assertIsNone(unknown.last_price)
        self.assertIsNone(unknown.is_trend_high)

    def test_service_error_keeps_previous_data(self):
        """Сбой Tinkoff API по пакету не роняет задачу и не портит данные."""
        share = _make_share(last_price=50.0, is_trend_high=True)

        def fail_fetch(figis):
            raise ConnectionError("tinkoff api down")

        with patch("dashboard.tasks.fetch_last_prices", side_effect=fail_fetch):
            update_last_price()  # не должно бросать исключений

        share.refresh_from_db()
        self.assertEqual(share.last_price, 50.0)
        self.assertTrue(share.is_trend_high)


class ShareDetailViewTests(TestCase):
    """Страница акции: 404 вместо 500, устойчивость к сбою графика."""

    def test_detail_missing_share_returns_404(self):
        response = self.client.get("/99999")
        self.assertEqual(response.status_code, 404)

    def get_detail_url(self, share):
        return f"/{share.pk}/"

    @patch("dashboard.views.get_graph", return_value="<div>graph</div>")
    def test_detail_renders_with_graph(self, mocked_graph):
        share = _make_share(last_price=123.45)
        response = self.client.get(f"/{share.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "graph")

    @patch(
        "dashboard.views.get_graph",
        side_effect=ConnectionError("tinkoff api down"),
    )
    def test_detail_survives_graph_failure(self, mocked_graph):
        """Сбой Tinkoff API не должен давать 500: страница открывается без графика."""
        share = _make_share(last_price=123.45)
        response = self.client.get(f"/{share.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<div>graph</div>")


class AddSharesCommandTests(TestCase):
    """Management-команда add_shares: get_or_create по figi с defaults."""

    def _run_command(self, api_instruments):
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        client = SimpleNamespace(
            instruments=SimpleNamespace(
                shares=lambda: SimpleNamespace(instruments=api_instruments)
            )
        )
        # MagicMock реализует протокол контекстного менеджера
        client_context = MagicMock()
        client_context.__enter__.return_value = client
        with patch(
            "dashboard.management.commands.add_shares.tinkoff_client",
            return_value=client_context,
        ):
            call_command("add_shares")

    def _instrument(self, **kwargs):
        from types import SimpleNamespace

        fields = dict(
            figi="BBG000B9XRY4",
            name="Apple",
            isin="US0378331005",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
        )
        fields.update(kwargs)
        return SimpleNamespace(**fields)

    def test_creates_new_shares(self):
        self._run_command([self._instrument()])
        self.assertEqual(Share.objects.count(), 1)
        self.assertEqual(Share.objects.first().ticker, "AAPL")

    def test_existing_share_updated_data_does_not_crash(self):
        """Атрибуты существующей акции изменились в API → не создаётся дубль
        и не падает IntegrityError (фикс: lookup только по figi)."""
        self._run_command([self._instrument(name="Apple Inc.")])
        self._run_command([self._instrument(name="Apple")])  # прежнее имя в API
        self.assertEqual(Share.objects.count(), 1)
        self.assertEqual(Share.objects.first().figi, "BBG000B9XRY4")


class ShareModelFormTests(TestCase):
    """Форма не должна позволять редактировать служебные поля."""

    def test_form_has_only_user_editable_fields(self):
        form = ShareModelForm()
        self.assertEqual(
            set(form.fields), {"figi", "isin", "name", "ticker", "currency"}
        )
        for forbidden in ("id", "last_price", "is_trend_high", "updated_at"):
            self.assertNotIn(forbidden, form.fields)

    def test_form_saves_without_touching_system_fields(self):
        """Сохранение формы не может подменить last_price даже через POST."""
        share = _make_share(last_price=77.7, is_trend_high=True)
        payload = {
            "figi": share.figi,
            "isin": share.isin,
            "name": "Apple Renamed",
            "ticker": share.ticker,
            "currency": share.currency,
            # Попытка подмены служебных полей через POST:
            "last_price": 1.23,
            "is_trend_high": False,
        }
        form = ShareModelForm(payload, instance=share)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        share.refresh_from_db()
        self.assertEqual(share.name, "Apple Renamed")
        self.assertEqual(share.last_price, 77.7)
        self.assertTrue(share.is_trend_high)
