from rest_framework import routers

from .views import NotificationViewSet, ShareViewSet, WatchlistEntryViewSet

router = routers.DefaultRouter()
router.register(r"shares", ShareViewSet)
router.register(r"watchlist", WatchlistEntryViewSet, basename="watchlistentry")
router.register(r"notifications", NotificationViewSet, basename="notification")
