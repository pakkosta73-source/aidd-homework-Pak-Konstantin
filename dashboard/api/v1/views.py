from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from dashboard.models import Notification, Share, WatchlistEntry

from .serializer import NotificationSerializer, ShareSerializer, WatchlistEntrySerializer


class ShareFilter(filters.FilterSet):
    class Meta:
        model = Share
        fields = ("name", "ticker")


class ShareViewSet(viewsets.ModelViewSet):
    serializer_class = ShareSerializer
    queryset = Share.objects.all()
    filter_backends = (OrderingFilter, filters.DjangoFilterBackend, SearchFilter)
    filterset_class = ShareFilter
    ordering_fields = ["name", "ticker"]
    search_fields = ["$name"]


class WatchlistEntryViewSet(viewsets.ModelViewSet):
    """ViewSet для записей списка наблюдения текущего пользователя."""

    serializer_class = WatchlistEntrySerializer

    def get_queryset(self):
        return WatchlistEntry.objects.filter(user=self.request.user).select_related("share")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для уведомлений текущего пользователя (только чтение)."""

    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related("share")
