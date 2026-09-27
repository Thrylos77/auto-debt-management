from django.urls import path

from .views import (
    LoginView, LogoutView, RefreshView, RequestOTPView, ResetPasswordView,
    SessionListView, SessionRevokeAllView, SessionRevokeView,
    VerifyTokenView, VerifyTwoFALoginView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("2fa/verify/", VerifyTwoFALoginView.as_view(), name="auth-2fa-verify"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("verify/", VerifyTokenView.as_view(), name="auth-verify"),
    path("password/forgot/", RequestOTPView.as_view(), name="auth-password-forgot"),
    path("password/reset/", ResetPasswordView.as_view(), name="auth-password-reset"),
    path("sessions/", SessionListView.as_view(), name="auth-session-list"),
    path("sessions/revoke-all/", SessionRevokeAllView.as_view(), name="auth-session-revoke-all"),
    path("sessions/<uuid:session_id>/", SessionRevokeView.as_view(), name="auth-session-revoke"),
]
