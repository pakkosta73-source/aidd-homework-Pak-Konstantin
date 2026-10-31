from django import forms

from .models import Share, WatchlistEntry


class ShareModelForm(forms.ModelForm):
    """Инструмент

    В форме только редактируемые пользователем поля: служебные поля
    (id, uid, last_price, is_trend_high, updated_at) заполняются системой
    и не должны показываться/подменяться пользователем.
    Ранее использовался fields="__all__" — через форму можно было подменить
    идентификаторы и цены.
    """

    class Meta:
        model = Share
        fields = ["figi", "isin", "name", "ticker", "currency"]


class WatchlistEntryModelForm(forms.ModelForm):
    """Запись наблюдения: акция, целевая цена и направление условия.

    Поле user не задаётся формой — оно подставляется во view
    из request.user, чтобы нельзя было создать наблюдение за другого пользователя.
    """

    class Meta:
        model = WatchlistEntry
        fields = ["share", "target_price", "condition"]
        labels = {
            "share": "Акция",
            "target_price": "Целевая цена",
            "condition": "Условие",
        }

    def clean_target_price(self):
        target_price = self.cleaned_data["target_price"]
        if target_price <= 0:
            raise forms.ValidationError(
                "Целевая цена должна быть положительным числом."
            )
        return target_price
