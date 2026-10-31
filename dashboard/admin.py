from django.contrib import admin

from dashboard.models import Notification, Share, WatchlistEntry


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("figi", "isin", "name", "ticker", "currency")
    search_fields = ("figi", "isin", "name", "ticker")
    fields = (
        "figi",
        "isin",
        "name",
        "ticker",
        "currency",
        "uid",
        "last_price",
        "is_trend_high",
    )


@admin.register(WatchlistEntry)
class WatchlistEntryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "share",
        "target_price",
        "condition",
        "notified",
        "created_at",
    )
    list_filter = ("condition", "notified")
    search_fields = ("user__email", "user__username", "share__ticker", "share__name")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "share", "created_at")
    search_fields = ("user__email", "user__username", "share__ticker", "share__name")
    readonly_fields = ("user", "share", "message", "created_at")
