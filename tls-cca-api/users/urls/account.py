"""User account, administration, and profile routes."""

from django.urls import path

from users.views import (
    AdminRequestPasswordResetView,
    AllUserHistoryListView,
    ChangeOwnPasswordView,
    ReactivateUserView,
    RegisterView,
    ResendInvitationView,
    UserDetailView,
    UserHistoryListView,
    UserListView,
    UserPreferenceView,
    UserRetrieveUpdateDestroyView,
)
from users.views.twofa import AdminReset2FAView

urlpatterns = [
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/register/", RegisterView.as_view(), name="register"),
    path("users/me/", UserDetailView.as_view(), name="user-detail"),
    path("users/me/password/change/", ChangeOwnPasswordView.as_view(), name="password-change-self"),
    path("users/me/preferences/", UserPreferenceView.as_view(), name="user-preferences"),
    path("users/<int:pk>/", UserRetrieveUpdateDestroyView.as_view(), name="user-rud"),
    path("users/<int:pk>/reactivate/", ReactivateUserView.as_view(), name="user-reactivate"),
    path("users/<int:pk>/invitation/resend/", ResendInvitationView.as_view(), name="user-invitation-resend"),
    path("users/<int:pk>/password/force-reset/", AdminRequestPasswordResetView.as_view(), name="password-force-reset"),
    path("users/<int:pk>/2fa/reset/", AdminReset2FAView.as_view(), name="user-2fa-reset"),
    path("users/history/", AllUserHistoryListView.as_view(), name="user-history-list"),
    path("users/history/<int:pk>/", UserHistoryListView.as_view(), name="user-history-detail"),
]
