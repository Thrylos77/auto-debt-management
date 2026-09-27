from .auth import LegacyTokenObtainPairView, LoginView, LogoutView, RefreshView, VerifyTwoFALoginView, VerifyTokenView
from .passwords import AdminChangePasswordView, ChangeOwnPasswordView, RequestOTPView, ResetPasswordView
from .preferences import UserPreferenceView
from .sessions import SessionListView, SessionRevokeAllView, SessionRevokeView
from .twofa import Disable2FAView, Enable2FAView, VerifySetup2FAView
from .users import AllUserHistoryListView, ReactivateUserView, RegisterView, UserDetailView, UserHistoryListView, UserListView, UserRetrieveUpdateDestroyView

# Legacy class aliases.
TokenObtainPairView = LegacyTokenObtainPairView
Login2FAView = VerifyTwoFALoginView
