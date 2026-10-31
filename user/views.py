from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.generic import View

from .forms import AuthForm, RegistrationForm


class AuthView(View):
    """Авторизация"""

    @staticmethod
    def get(request):
        return render(request, "user/auth.html", {"form": AuthForm})

    @staticmethod
    def post(request):
        form = AuthForm(request.POST)
        # Ранее данные брались напрямую из form.data без form.is_valid():
        # при отсутствии поля POST падал KeyError вместо показа ошибки.
        if form.is_valid():
            # Email уже нормализован в AuthForm.clean_email (lower + strip).
            user = authenticate(
                request,
                username=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )

            if user is not None:
                login(request, user)
                return redirect("dashboard:index")

        return render(
            request,
            "user/auth.html",
            {"form": form, "error": "Неверный логин или пароль! Повторите попытку."},
        )


class RegistrationView(View):
    """Регистрация"""

    @staticmethod
    def get(request):
        return render(request, "user/registration.html", {"form": RegistrationForm})

    @staticmethod
    def post(request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard:index")
        else:
            # Ранно разобралось только form.errors["__all__"]: при ошибке
            # уровня поля (например, некорректный формат e-mail) не попадал
            # KeyError и пользователь получал 500. Берём первую доступную
            # ошибку вне зависимости от её уровня.
            errors = list(form.non_field_errors())
            if not errors:
                errors = [e for errs in form.errors.values() for e in errs]
            return render(
                request,
                "user/registration.html",
                {"form": form, "error": str(errors[0])},
            )


class LogoutView(View):
    """Выход"""

    @staticmethod
    def get(request):
        logout(request)
        return redirect("dashboard:index")
