from .views import (
    LogoutView, RegisterView, UserListView, UserDetailView, 
    ResetPasswordView, TokenObtainPairView, UserHistoryListView, 
    ChangeOwnPasswordView, AllUserHistoryListView, AdminChangePasswordView,
    UserRetrieveUpdateDestroyView, ReactivateUserView, RequestOTPView,
)
from .views_2fa import (
    Enable2FAView, Disable2FAView,
    Login2FAView, VerifySetup2FAView, 
)