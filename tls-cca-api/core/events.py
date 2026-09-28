"""Application-level domain events.

The events live in ``core`` so platform consumers such as audit can listen to
business and identity events without importing concrete business applications.
"""

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

customer_created = Signal()
customer_updated = Signal()
customer_activated = Signal()
customer_deactivated = Signal()
portfolio_created = Signal()
portfolio_assigned = Signal()
portfolio_transferred = Signal()
credit_sale_status_changed = Signal()
recovery_created = Signal()
debt_status_updated = Signal()
