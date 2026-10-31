from django.contrib import admin

from dashboard.models import Notification, Share, WatchlistEntry


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("ticker", "name", "isin", "currency", "last_price", "is_trend_high", "updated_at")
    list_filter = ("currency", "is_trend_high")
    search_fields = ("figi", "isin", "name", "ticker")
    readonly_fields = ("last_price", "is_trend_high", "updated_at")
    exclude = ("uid",)


@admin.register(WatchlistEntry)
class WatchlistEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "share", "target_price", "condition", "notified", "created_at")
    list_filter = ("condition", "notified")
    search_fields = ("user__username", "share__ticker", "share__name")
    readonly_fields = ("created_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "share", "message", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "share__ticker", "message")
    readonly_fields = ("user", "share", "message", "created_at")
