"""Тесты логики персонального мониторинга: условия, дедупликация, перевзвод."""

from unittest.mock import patch

from django.test import TestCase

from dashboard.models import Notification, Share, WatchlistEntry
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


def _make_user():
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username="u1@example.com",
        email="u1@example.com",
        password="test-password-123",
    )


def _make_entry(share, **kwargs):
    fields = dict(
        target_price=100.0,
        condition=WatchlistEntry.CONDITION_ABOVE,
        notified=False,
    )
    fields.update(kwargs)
    return WatchlistEntry.objects.create(share=share, **fields)


def _run_update(prices: dict):
    with patch("dashboard.tasks.fetch_last_prices", return_value=prices):
        update_last_price()


class WatchlistConditionTests(TestCase):
    """Проверка срабатывания условий выше/ниже цели."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user()
        cls.share = _make_share()

    def test_above_condition(self):
        """above: срабатывает при price >= target, не срабатывает при price < target."""
        entry = _make_entry(self.share, user=self.user, target_price=100.0)

        _run_update({self.share.figi: 100.0})  # ровно цель — срабатывает (>=)
        entry.refresh_from_db()
        self.assertTrue(entry.notified)
        self.assertEqual(Notification.objects.count(), 1)

    def test_above_condition_not_fired_below_target(self):
        entry = _make_entry(self.share, user=self.user, target_price=100.0)

        _run_update({self.share.figi: 99.99})
        entry.refresh_from_db()
        self.assertFalse(entry.notified)
        self.assertEqual(Notification.objects.count(), 0)

    def test_below_condition(self):
        """below: срабатывает при price <= target, не срабатывает при price > target."""
        entry = _make_entry(
            self.share, user=self.user, condition=WatchlistEntry.CONDITION_BELOW
        )

        _run_update({self.share.figi: 100.0})  # ровно цель — срабатывает (<=)
        entry.refresh_from_db()
        self.assertTrue(entry.notified)
        self.assertEqual(Notification.objects.count(), 1)

    def test_below_condition_not_fired_above_target(self):
        entry = _make_entry(
            self.share, user=self.user, condition=WatchlistEntry.CONDITION_BELOW
        )

        _run_update({self.share.figi: 100.01})
        entry.refresh_from_db()
        self.assertFalse(entry.notified)
        self.assertEqual(Notification.objects.count(), 0)


class NotificationDeduplicationTests(TestCase):
    """Уведомление об одном событии отправляется один раз."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user()
        cls.share = _make_share()
        cls.entry = _make_entry(cls.share, user=cls.user, target_price=100.0)

    def test_no_duplicate_notification(self):
        """После срабатывания повторный updates не создаёт второе уведомление."""
        _run_update({self.share.figi: 150.0})
        self.assertEqual(Notification.objects.count(), 1)

        _run_update({self.share.figi: 151.0})
        _run_update({self.share.figi: 152.0})
        self.assertEqual(Notification.objects.count(), 1)  # дубликата нет

    def test_reset_arms_entry_again(self):
        """После ручного перевзвода (notified=False) уведомление создаётся снова."""
        _run_update({self.share.figi: 150.0})
        self.assertEqual(Notification.objects.count(), 1)

        self.entry.refresh_from_db()
        self.assertTrue(self.entry.notified)

        WatchlistEntry.objects.filter(pk=self.entry.pk).update(notified=False)
        _run_update({self.share.figi: 155.0})
        self.assertEqual(Notification.objects.count(), 2)

    def test_share_without_price_is_skipped(self):
        """Акция без цены (None) не проверяется — уведомления нет."""
        _run_update({self.share.figi: None, "unknown_figi": 999.0})
        self.share.refresh_from_db()
        self.entry.refresh_from_db()
        self.assertIsNone(self.share.last_price)
        self.assertFalse(self.entry.notified)
        self.assertEqual(Notification.objects.count(), 0)

    def test_notification_message_content(self):
        """Текст уведомления содержит тикер, текущую цену и целевой уровень."""
        _run_update({self.share.figi: 123.45})
        notification = Notification.objects.first()
        self.assertIsNotNone(notification)
        self.assertIn("AAPL", notification.message)
        self.assertIn("123.45", notification.message)
        self.assertIn("100.00", notification.message)
        self.assertEqual(notification.user, self.entry.user)
