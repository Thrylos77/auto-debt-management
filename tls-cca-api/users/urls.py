from django.urls import path

from .views import (
    AdminChangePasswordView, ChangeOwnPasswordView, Disable2FAView, Enable2FAView,
    ReactivateUserView, RegisterView, ResetPasswordView, RequestOTPView,
    UserDetailView,
    UserListView, UserPreferenceView, UserRetrieveUpdateDestroyView, VerifySetup2FAView,
)

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", UserDetailView.as_view(), name="user-detail"),
    path("me/password/change/", ChangeOwnPasswordView.as_view(), name="password-change-self"),
    path("me/preferences/", UserPreferenceView.as_view(), name="user-preferences"),
    path("me/2fa/setup/", Enable2FAView.as_view(), name="2fa-setup"),
    path("me/2fa/verify-setup/", VerifySetup2FAView.as_view(), name="2fa-verify-setup"),
    path("me/2fa/disable/", Disable2FAView.as_view(), name="2fa-disable"),
    path("<int:pk>/", UserRetrieveUpdateDestroyView.as_view(), name="user-rud"),
    path("<int:pk>/reactivate/", ReactivateUserView.as_view(), name="user-reactivate"),
    path("<int:pk>/password/force-reset/", AdminChangePasswordView.as_view(), name="password-force-reset"),
]
