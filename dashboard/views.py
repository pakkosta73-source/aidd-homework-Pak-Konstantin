from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from config.settings import logger

from .forms import ShareModelForm, WatchlistEntryModelForm
from .models import Notification, Share, WatchlistEntry
from .services.graph import get_graph


class IsUserAuthenticatedMixin(UserPassesTestMixin):
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


class ShareDetailView(View):
    @staticmethod
    def get(request, pk):
        # Share.objects.get(id=pk) при несуществующем pk кидал DoesNotExist
        # → пользователь получал 500 вместо 404.
        share = get_object_or_404(Share, id=pk)

        try:
            plot_div = get_graph(share)
        except Exception:
            # Недоступный Tinkoff API не должен ломать страницу акции —
            # показываем её без графика, ошибка фиксируется в логах.
            logger.exception(f"Failed to build graph for share id {share.id}")
            plot_div = ""

        return render(
            request,
            "dashboard/detail.html",
            {"plot_div": plot_div, "share": share},
        )


class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
    """Добавление инструмента"""

    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareUpdateView(IsUserAuthenticatedMixin, UpdateView):
    """Редактирование инструмента"""

    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Удаление инструмента"""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")


class UserOwnedQuerySetMixin:
    """Ограничивает доступ к записи только её владельцем.

    Чужие записи и несуществующие pk обрабатываются одинаково — 404.
    """

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class WatchlistListView(IsUserAuthenticatedMixin, ListView):
    """Личный список наблюдения пользователя (вместе с текущими ценами)"""

    template_name = "dashboard/watchlist.html"
    context_object_name = "entries"

    def get_queryset(self):
        return (
            WatchlistEntry.objects.filter(user=self.request.user)
            .select_related("share")
            .order_by("-created_at")
        )


class WatchlistCreateView(IsUserAuthenticatedMixin, CreateView):
    """Добавление записи наблюдения"""

    template_name = "dashboard/watchlist_form.html"
    form_class = WatchlistEntryModelForm
    success_url = reverse_lazy("dashboard:watchlist")

    def form_valid(self, form):
        form.instance.user = self.request.user
        if WatchlistEntry.objects.filter(
            user=self.request.user, share=form.cleaned_data["share"]
        ).exists():
            # Бизнес-правило: одну акцию нельзя добавить в личный список дважды.
            form.add_error(
                "share",
                "Эта акция уже есть в вашем списке наблюдения.",
            )
            return self.form_invalid(form)
        response = super().form_valid(form)
        messages.success(self.request, "Наблюдение добавлено.")
        return response


class WatchlistDeleteView(UserOwnedQuerySetMixin, IsUserAuthenticatedMixin, DeleteView):
    """Удаление записи наблюдения (только своей)"""

    model = WatchlistEntry
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:watchlist")


class WatchlistResetView(UserOwnedQuerySetMixin, IsUserAuthenticatedMixin, View):
    """Ручной перевзвод алерта: notified=False, условие снова отслеживается"""

    http_method_names = ["post"]

    def post(self, request, pk):
        updated = WatchlistEntry.objects.filter(pk=pk, user=request.user).update(
            notified=False
        )
        if updated:
            messages.success(
                request,
                "Алерт перевзведён: условие снова отслеживается.",
            )
        return redirect("dashboard:watchlist")


class NotificationListView(IsUserAuthenticatedMixin, ListView):
    """Список внутрисайтовых уведомлений пользователя"""

    template_name = "dashboard/notification_list.html"
    context_object_name = "notifications"

    def get_queryset(self):
        return (
            Notification.objects.filter(user=self.request.user)
            .select_related("share")
            .order_by("-created_at")
        )
