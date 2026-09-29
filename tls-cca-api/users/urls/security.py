"""Two-factor authentication and session-security routes."""

from django.urls import path

from users.views import Enable2FAView, SessionListView, SessionRevokeAllView, SessionRevokeView, VerifySetup2FAView

urlpatterns = [
    path("users/me/2fa/setup/", Enable2FAView.as_view(), name="2fa-setup"),
    path("users/me/2fa/verify-setup/", VerifySetup2FAView.as_view(), name="2fa-verify-setup"),
    path("auth/sessions/", SessionListView.as_view(), name="auth-session-list"),
    path("auth/sessions/revoke-all/", SessionRevokeAllView.as_view(), name="auth-session-revoke-all"),
    path("auth/sessions/<uuid:session_id>/", SessionRevokeView.as_view(), name="auth-session-revoke"),
]
