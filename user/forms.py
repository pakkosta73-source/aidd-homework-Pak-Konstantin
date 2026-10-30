from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

INPUT_ATTRS = {"class": "form-control my-3 p-4"}


class RegistrationForm(forms.Form):
    """Форма регистрации пользователей"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={**INPUT_ATTRS, "placeholder": "Email"}),
    )
    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={**INPUT_ATTRS, "placeholder": "Пароль"}),
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={**INPUT_ATTRS, "placeholder": "Повторите пароль"}
        ),
    )

    def clean(self):
        super().clean()
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(["Введенные пароли не совпадают"])

        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email=email).exists():
            raise ValidationError(
                [
                    "Данный e-mail уже зарегистрирован! Введите другой e-mail или"
                    " воспользуйтесь формой авторизации."
                ]
            )
        return self.cleaned_data

    def save(self):
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]
        User.objects.create_user(email, email, password)
        return authenticate(username=email, password=password)


class AuthForm(forms.Form):
    """Форма авторизации пользователей"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={**INPUT_ATTRS, "placeholder": "Email"}),
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={**INPUT_ATTRS, "placeholder": "Пароль"}),
    )
