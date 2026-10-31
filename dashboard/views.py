from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from .forms import ShareModelForm, WatchlistEntryForm
from .models import Notification, Share, WatchlistEntry
from .services.graph import get_graph
from .services.market_data import get_last_data

SUCCESS_URL = reverse_lazy("dashboard:index")


class IsUserAuthenticatedMixin(UserPassesTestMixin):
    """Проверка авторизации пользователя с перенаправлением на главную."""

    def test_func(self):
        return self.request.user.is_authenticated

    @staticmethod
    def handle_no_permission():
        return redirect("dashboard:index")


class ShareListView(ListView):
    """Список акций"""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shares = self.get_queryset()
        # Динамически загружаем цены для каждой акции
        for share in shares:
            try:
                price, _ = get_last_data(share)
                share.last_price = price
                # Определяем тренд
                if share.last_price is not None and share.is_trend_high is not None:
                    share.is_trend_high = share.last_price >= (share._old_price if hasattr(share, '_old_price') else 0)
                share._old_price = share.last_price
            except Exception:
                share.last_price = share.last_price  # оставляем цену из базы если API недоступен
        context["share_list"] = shares
        return context


class ShareDetailView(DetailView):
    """Детальная информация об акции с графиком"""

    model = Share
    template_name = "dashboard/detail.html"
    context_object_name = "share"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plot_div"] = get_graph(self.object)
        return context


class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
    """Добавление инструмента"""

    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = SUCCESS_URL


class ShareUpdateView(IsUserAuthenticatedMixin, UpdateView):
    """Редактирование инструмента"""

    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = SUCCESS_URL


class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Удаление инструмента"""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = SUCCESS_URL


class WatchlistListView(IsUserAuthenticatedMixin, ListView):
    """Список наблюдения пользователя"""

    model = WatchlistEntry
    template_name = "dashboard/watchlist.html"
    context_object_name = "watchlist_entries"

    def get_queryset(self):
        return WatchlistEntry.objects.filter(user=self.request.user).select_related("share")


class WatchlistCreateView(IsUserAuthenticatedMixin, CreateView):
    """Добавление акции в список наблюдения"""

    model = WatchlistEntry
    template_name = "dashboard/watchlist_form.html"
    form_class = WatchlistEntryForm
    success_url = reverse_lazy("dashboard:watchlist")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class WatchlistDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Удаление акции из списка наблюдения"""

    model = WatchlistEntry
    template_name = "dashboard/watchlist_confirm_delete.html"
    success_url = reverse_lazy("dashboard:watchlist")

    def get_queryset(self):
        return WatchlistEntry.objects.filter(user=self.request.user)


class WatchlistResetView(IsUserAuthenticatedMixin, View):
    """Сброс флага уведомления для повторной активации"""

    def post(self, request, pk):
        entry = get_object_or_404(WatchlistEntry, pk=pk, user=request.user)
        entry.notified = False
        entry.save(update_fields=["notified"])
        return redirect("dashboard:watchlist")


class NotificationListView(IsUserAuthenticatedMixin, ListView):
    """Список уведомлений пользователя"""

    model = Notification
    template_name = "dashboard/notification_list.html"
    context_object_name = "notifications"

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related("share")
