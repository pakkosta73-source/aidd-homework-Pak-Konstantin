"""Тесты аутентификации: регистрация, вход, нормализация email (BP-6, FR-3, FR-4)."""

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class RegistrationTests(TestCase):
    email = "Tester@Example.COM"
    password = "qwerty12345"

    def register(self, email=None, password1=None, password2=None, **kwargs):
        return self.client.post(
            "/user/registration/",
            {
                "email": email if email is not None else self.email,
                "password1": password1 if password1 is not None else self.password,
                "password2": password2 if password2 is not None else self.password,
            },
            **kwargs,
        )

    def test_registration_success_and_autologin(self):
        """Успешная регистрация: пользователь создан, username=email, автологин."""
        response = self.register(follow=True)
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(email__iexact=self.email)
        self.assertEqual(user.username, user.email.lower())
        self.assertTrue(user.is_authenticated or self.client.session.items())

        self.assertIn("_auth_user_id", self.client.session)

    def test_registration_normalizes_email_case(self):
        """Email приводится к нижнему регистру (иначе вход case-sensitive ломается)."""
        response = self.register(follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email__iexact=self.email)
        self.assertEqual(user.email, self.email.lower())

    def test_registration_duplicate_email_rejected(self):
        User.objects.create_user(self.email.lower(), self.email.lower(), self.password)
        response = self.register(
            email=self.email.upper(),
            password1=self.password,
            password2=self.password,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertIn("e-mail", response.context.get("error", "").lower())

    def test_registration_passwords_mismatch_rejected(self):
        response = self.register(password2=self.password + "x")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        self.assertIn("не совпадают", response.context.get("error", ""))


class AuthTests(TestCase):
    email = "tester@example.com"
    password = "qwerty12345"

    def setUp(self):
        User.objects.create_user(self.email, self.email, self.password)

    def test_login_success_redirects_to_list(self):
        response = self.client.post(
            "/user/login/",
            {"email": self.email, "password": self.password},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_case_insensitive_email(self):
        response = self.client.post(
            "/user/login/",
            {"email": self.email.upper(), "password": self.password},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_wrong_password_shows_error(self):
        response = self.client.post(
            "/user/login/",
            {"email": self.email, "password": "wrong-password"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertIn("Неверный логин или пароль".encode(), response.content)

    def test_login_missing_fields_no_server_error(self):
        """Обращение с отсутствующим полем POST не должно ронять приложение."""
        response = self.client.post("/user/login/", {"email": self.email})
        self.assertEqual(response.status_code, 200)
