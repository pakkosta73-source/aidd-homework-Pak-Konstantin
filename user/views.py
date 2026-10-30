from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.generic import View

from .forms import AuthForm, RegistrationForm


def _render_form(request, template, form, error=None):
    """Отрисовать страницу с формой авторизации/регистрации."""
    return render(request, template, {"form": form, "error": error})


class AuthView(View):
    """Авторизация"""

    @staticmethod
    def get(request):
        return _render_form(request, "user/auth.html", AuthForm())

    @staticmethod
    def post(request):
        form = AuthForm(request.POST)
        if not form.is_valid():
            return _render_form(
                request, "user/auth.html", form,
                error="Заполните все поля формы.",
            )
        user = authenticate(
            request,
            username=form.cleaned_data["email"].lower(),
            password=form.cleaned_data["password"],
        )
        if user is not None:
            login(request, user)
            return redirect("dashboard:index")
        return _render_form(
            request, "user/auth.html", form,
            error="Неверный логин или пароль! Повторите попытку.",
        )


class RegistrationView(View):
    """Регистрация"""

    @staticmethod
    def get(request):
        return _render_form(request, "user/registration.html", RegistrationForm())

    @staticmethod
    def post(request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard:index")
        error = form.errors.get("__all__", [{}])[0]
        if hasattr(error, "message"):
            error = error.message
        return _render_form(
            request, "user/registration.html", form,
            error=error,
        )


class LogoutView(View):
    """Выход"""

    @staticmethod
    def get(request):
        logout(request)
        return redirect("dashboard:index")
