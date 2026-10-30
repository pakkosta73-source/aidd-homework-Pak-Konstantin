from django import forms
from django.core.exceptions import ValidationError
from tinkoff.invest import Client

from config.settings import TINKOFF_TOKEN
from .models import Share


class ShareModelForm(forms.ModelForm):
    """Инструмент"""

    class Meta:
        model = Share
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data["name"]
        # Пытаемся найти инструмент по имени через API Tinkoff
        try:
            with Client(TINKOFF_TOKEN) as client:
                shares = client.instruments.shares()
                found = None
                for share in shares.instruments:
                    if share.name.lower() == name.lower():
                        found = share
                        break
                if found is None:
                    raise ValidationError(
                        f"Инструмент с названием «{name}» не найден в реестре."
                    )
                # Проверяем, не добавлена ли уже эта акция
                if Share.objects.filter(figi=found.figi).exists():
                    raise ValidationError(
                        f"Акция «{found.name}» уже добавлена в систему."
                    )
                # Сохраняем данные для автозаполнения
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
            instance.figi = self._api_data["figi"]
            instance.isin = self._api_data["isin"]
            instance.ticker = self._api_data["ticker"]
            instance.currency = self._api_data["currency"]
            instance.uid = self._api_data["uid"]
        if commit:
            instance.save()
        return instance
