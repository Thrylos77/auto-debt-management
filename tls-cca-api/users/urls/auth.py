"""Authentication and public onboarding/recovery routes."""

from django.urls import path

from users.views import (
    AcceptInvitationView,
    LoginView,
    LogoutView,
    RefreshView,
    RequestPasswordResetView,
    ResetPasswordView,
    TwoFARecoverySetupView,
    TwoFARecoveryVerifyView,
    VerifyInitialTwoFAView,
    VerifyInvitationTwoFAView,
    VerifyTokenView,
    VerifyTwoFALoginView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/2fa/verify/", VerifyTwoFALoginView.as_view(), name="auth-2fa-verify"),
    path("auth/2fa/enroll/verify/", VerifyInitialTwoFAView.as_view(), name="auth-2fa-enroll-verify"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/verify/", VerifyTokenView.as_view(), name="auth-verify"),
    path("auth/invitation/accept/", AcceptInvitationView.as_view(), name="auth-invitation-accept"),
    path("auth/invitation/verify-2fa/", VerifyInvitationTwoFAView.as_view(), name="auth-invitation-verify-2fa"),
    path("auth/2fa/recovery/setup/", TwoFARecoverySetupView.as_view(), name="auth-2fa-recovery-setup"),
    path("auth/2fa/recovery/verify/", TwoFARecoveryVerifyView.as_view(), name="auth-2fa-recovery-verify"),
    path("auth/password/forgot/", RequestPasswordResetView.as_view(), name="auth-password-forgot"),
    path("auth/password/reset/", ResetPasswordView.as_view(), name="auth-password-reset"),
]
