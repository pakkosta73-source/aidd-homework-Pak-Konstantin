from django.urls import include, path

from dashboard.views import (
    NotificationListView,
    ShareCreateView,
    ShareDeleteView,
    ShareDetailView,
    ShareListView,
    ShareUpdateView,
    WatchlistCreateView,
    WatchlistDeleteView,
    WatchlistListView,
    WatchlistResetView,
)

app_name = "dashboard"

urlpatterns = [
    path("", ShareListView.as_view(), name="index"),
    path("<int:pk>", ShareDetailView.as_view(), name="detail"),
    path("create", ShareCreateView.as_view(), name="create"),
    path("update/<int:pk>", ShareUpdateView.as_view(), name="update"),
    path("delete/<int:pk>", ShareDeleteView.as_view(), name="delete"),
    path("watchlist/", WatchlistListView.as_view(), name="watchlist"),
    path("watchlist/add/", WatchlistCreateView.as_view(), name="watchlist_add"),
    path("watchlist/remove/<int:pk>/", WatchlistDeleteView.as_view(), name="watchlist_remove"),
    path("watchlist/reset/<int:pk>/", WatchlistResetView.as_view(), name="watchlist_reset"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("api/", include("dashboard.api.urls")),
]
