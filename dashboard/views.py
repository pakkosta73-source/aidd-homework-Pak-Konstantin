from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import ShareModelForm
from .models import Share
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
