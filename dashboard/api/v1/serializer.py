from rest_framework import serializers

from dashboard.models import Notification, Share, WatchlistEntry


class ShareSerializer(serializers.ModelSerializer):
    """Сериализатор для REST API акций."""

    class Meta:
        model = Share
        fields = (
            "id",
            "figi",
            "isin",
            "name",
            "ticker",
            "currency",
            "last_price",
            "is_trend_high",
            "updated_at",
        )


class WatchlistEntrySerializer(serializers.ModelSerializer):
    """Сериализатор для записей списка наблюдения."""

    share_name = serializers.CharField(source="share.name", read_only=True)
    share_ticker = serializers.CharField(source="share.ticker", read_only=True)
    current_price = serializers.FloatField(source="share.last_price", read_only=True)

    class Meta:
        model = WatchlistEntry
        fields = (
            "id",
            "share",
            "share_name",
            "share_ticker",
            "target_price",
            "condition",
            "notified",
            "current_price",
            "created_at",
        )
        read_only_fields = ("user", "notified", "created_at")


class NotificationSerializer(serializers.ModelSerializer):
    """Сериализатор для уведомлений."""

    share_name = serializers.CharField(source="share.name", read_only=True)
    share_ticker = serializers.CharField(source="share.ticker", read_only=True)

    class Meta:
        model = Notification
        fields = ("id", "share", "share_name", "share_ticker", "message", "created_at")
        read_only_fields = fields
