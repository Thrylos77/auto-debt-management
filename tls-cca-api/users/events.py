from django.dispatch import Signal

user_deactivated = Signal()
user_reactivated = Signal()
user_password_changed = Signal()
user_login_succeeded = Signal()
user_login_failed = Signal()
