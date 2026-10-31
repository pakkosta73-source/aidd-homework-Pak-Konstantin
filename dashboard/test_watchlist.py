"""Тесты логики проверки целевых цен и уведомлений (список наблюдения)."""

from django.test import TestCase
from django.urls import reverse

from dashboard.models import Notification, Share, WatchlistEntry
from dashboard.tasks import _check_watchlist_conditions


class WatchlistConditionTests(TestCase):
    """Проверка срабатывания условий, дедупликации и перевзвода алертов."""

    def setUp(self):
        self.user = self._create_user("testuser", "test@example.com")
        self.client.force_login(self.user)
        self.share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=100.50,
            is_trend_high=True,
        )

    @staticmethod
    def _create_user(username, email):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(
            username=username, email=email, password="S3cretPass!"
        )

    def _create_entry(self, condition, target_price):
        return WatchlistEntry.objects.create(
            user=self.user,
            share=self.share,
            target_price=target_price,
            condition=condition,
        )

    def test_above_target_creates_notification(self):
        """Цена >= цели (above): уведомление создаётся, флаг ставится."""
        entry = self._create_entry(WatchlistEntry.CONDITION_ABOVE, target_price=100.0)

        _check_watchlist_conditions()

        entry.refresh_from_db()
        self.assertTrue(entry.notified)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        notification = Notification.objects.get(user=self.user)
        self.assertIn(self.share.ticker, notification.message)

    def test_below_target_creates_notification(self):
        """Цена <= цели (below): уведомление создаётся."""
        entry = self._create_entry(WatchlistEntry.CONDITION_BELOW, target_price=150.0)

        _check_watchlist_conditions()

        entry.refresh_from_db()
        self.assertTrue(entry.notified)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_condition_not_met_no_notification(self):
        """Условие не выполнено: уведомления нет, флаг не ставится."""
        entry = self._create_entry(WatchlistEntry.CONDITION_BELOW, target_price=50.0)

        _check_watchlist_conditions()

        entry.refresh_from_db()
        self.assertFalse(entry.notified)
        self.assertEqual(Notification.objects.count(), 0)

    def test_no_duplicate_notification_on_repeated_check(self):
        """Повторный запуск проверки не создаёт дубликат уведомления."""
        self._create_entry(WatchlistEntry.CONDITION_ABOVE, target_price=100.0)

        _check_watchlist_conditions()
        _check_watchlist_conditions()

        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_reset_rearms_alert(self):
        """После ручного перевзвода алерт срабатывает заново."""
        entry = self._create_entry(WatchlistEntry.CONDITION_ABOVE, target_price=100.0)

        _check_watchlist_conditions()
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

        response = self.client.post(
            reverse("dashboard:watchlist_reset", args=[entry.pk])
        )

        self.assertRedirects(response, reverse("dashboard:watchlist"))
        entry.refresh_from_db()
        self.assertFalse(entry.notified)

        _check_watchlist_conditions()
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 2)
