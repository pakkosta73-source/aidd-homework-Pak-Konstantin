from django.conf import settings
from django.db import models


class Share(models.Model):
    """Акция"""

    figi = models.CharField(max_length=255, unique=True)
    isin = models.CharField(max_length=255)
    name = models.CharField(max_length=255, verbose_name="Наименование компании")
    ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
    currency = models.CharField(max_length=20, verbose_name="Валюта")
    uid = models.CharField(max_length=255, unique=True)
    last_price = models.FloatField(blank=True, null=True, verbose_name="Текущая цена")
    is_trend_high = models.BooleanField(
        blank=True, null=True, verbose_name="Растет цена"
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def __str__(self):
        return f"{self.ticker} — {self.name}"


class WatchlistEntry(models.Model):
    """Запись в списке наблюдения пользователя"""

    CONDITION_ABOVE = "above"
    CONDITION_BELOW = "below"
    CONDITION_CHOICES = [
        (CONDITION_ABOVE, "Цена выше цели"),
        (CONDITION_BELOW, "Цена ниже цели"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Пользователь"
    )
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, verbose_name="Акция"
    )
    target_price = models.FloatField(verbose_name="Целевая цена")
    condition = models.CharField(
        max_length=10, choices=CONDITION_CHOICES, verbose_name="Условие"
    )
    notified = models.BooleanField(default=False, verbose_name="Уведомление отправлено")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Запись наблюдения"
        verbose_name_plural = "Записи наблюдения"
        unique_together = ("user", "share")

    def __str__(self):
        return f"{self.user.username} — {self.share.ticker} ({self.condition}: {self.target_price})"


class Notification(models.Model):
    """Уведомление пользователя"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Пользователь"
    )
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, verbose_name="Акция"
    )
    message = models.TextField(verbose_name="Сообщение")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.username} — {self.share.ticker}: {self.message}"
