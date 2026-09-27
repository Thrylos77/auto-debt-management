from django.dispatch import Signal

user_deactivated = Signal()
user_reactivated = Signal()
user_password_changed = Signal()
user_login_succeeded = Signal()
user_login_failed = Signal()
user_twofa_success = Signal()
user_twofa_failure = Signal()
user_twofa_enabled = Signal()
user_twofa_disabled = Signal()
user_logout = Signal()
user_session_revoked = Signal()
