from django.contrib import admin

from dashboard.models import Share


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("ticker", "name", "isin", "currency", "last_price", "is_trend_high", "updated_at")
    list_filter = ("currency", "is_trend_high")
    search_fields = ("figi", "isin", "name", "ticker")
    readonly_fields = ("last_price", "is_trend_high", "updated_at")
    exclude = ("uid",)
