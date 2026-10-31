from django import forms
from django.core.exceptions import ValidationError

from .models import Share, WatchlistEntry
from .services.tinkoff_client import get_client


class ShareModelForm(forms.ModelForm):
    """Форма добавления/редактирования инструмента"""

    class Meta:
        model = Share
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data["name"]
        try:
            with get_client() as client:
                shares = client.instruments.shares()
                found = next(
                    (s for s in shares.instruments if s.name.lower() == name.lower()),
                    None,
                )
                if found is None:
                    raise ValidationError(
                        f"Инструмент с названием «{name}» не найден в реестре."
                    )
                if Share.objects.filter(figi=found.figi).exists():
                    raise ValidationError(
                        f"Акция «{found.name}» уже добавлена в систему."
                    )
                self._api_data = {
                    "figi": found.figi,
                    "isin": found.isin,
                    "ticker": found.ticker,
                    "currency": found.currency,
                    "uid": found.uid,
                }
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Ошибка при поиске инструмента: {e}")
        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        if hasattr(self, "_api_data"):
            for field, value in self._api_data.items():
                setattr(instance, field, value)
        if commit:
            instance.save()
        return instance


class WatchlistEntryForm(forms.ModelForm):
    """Форма добавления акции в список наблюдения"""

    class Meta:
        model = WatchlistEntry
        fields = ["share", "target_price", "condition"]
        widgets = {
            "share": forms.Select(attrs={"class": "form-select"}),
            "target_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "condition": forms.Select(attrs={"class": "form-select"}),
        }
