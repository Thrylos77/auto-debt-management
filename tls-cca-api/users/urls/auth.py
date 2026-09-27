"""Authentication and password-recovery routes."""

from django.urls import path

from users.views import LoginView, LogoutView, RefreshView
from users.views import RequestOTPView, ResetPasswordView, VerifyTokenView
from users.views import VerifyTwoFALoginView


urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/2fa/verify/", VerifyTwoFALoginView.as_view(), name="auth-2fa-verify"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/verify/", VerifyTokenView.as_view(), name="auth-verify"),
    path("auth/password/forgot/", RequestOTPView.as_view(), name="auth-password-forgot"),
    path("auth/password/reset/", ResetPasswordView.as_view(), name="auth-password-reset"),
]
