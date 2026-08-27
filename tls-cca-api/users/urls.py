""" users/urls.py """

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    Login2FAView, RegisterView, UserDetailView, UserListView,
    UserRetrieveUpdateDestroyView, ReactivateUserView, AllUserHistoryListView,
    UserHistoryListView, AdminChangePasswordView, ChangeOwnPasswordView,
    RequestOTPView, ResetPasswordView, LogoutView, TokenObtainPairView, 
    VerifySetup2FAView, Enable2FAView, Disable2FAView, 
)


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', UserDetailView.as_view(), name='user-detail'),
    path('', UserListView.as_view(), name='user-list'),
    path('<int:pk>/', UserRetrieveUpdateDestroyView.as_view(), name='user-rud'),
    path('<int:pk>/reactivate/', ReactivateUserView.as_view(), name='user-reactivate'),
    
    path('history/<int:pk>/', UserHistoryListView.as_view(), name='user-history-detail'),
    path('history/', AllUserHistoryListView.as_view(), name='user-history-list'),

    path('change-password/<int:pk>/', AdminChangePasswordView.as_view(), name='change-password'),
    path('change-own-password/', ChangeOwnPasswordView.as_view(), name='change-own-password'),
    path('request-otp/', RequestOTPView.as_view(), name='request-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    path('token/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # 2FA endpoints
    path('2fa/enable/', Enable2FAView.as_view(), name='2fa-enable'),
    path('2fa/verify-setup/', VerifySetup2FAView.as_view(), name='2fa-verify-setup'),
    path('2fa/disable/', Disable2FAView.as_view(), name='2fa-disable'),
    path('2fa/login/', Login2FAView.as_view(), name='2fa-login'),
   
]
