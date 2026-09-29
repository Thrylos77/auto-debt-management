"""Audit receivers for identity, session, security, and domain events."""

from django.dispatch import receiver

from audit.services import AuditService
from core.events import (
    credit_sale_status_changed,
    customer_activated,
    customer_created,
    customer_deactivated,
    customer_updated,
    debt_status_updated,
    portfolio_assigned,
    portfolio_created,
    portfolio_transferred,
    recovery_created,
    user_deactivated,
    user_invitation_created,
    user_login_failed,
    user_login_succeeded,
    user_logout,
    user_password_changed,
    user_password_initialized,
    user_password_reset_completed,
    user_password_reset_requested,
    user_reactivated,
    user_session_revoked,
    user_twofa_enabled,
    user_twofa_failure,
    user_twofa_reset,
    user_twofa_success,
)


@receiver(user_login_succeeded)
def audit_login_success(
    sender,
    user,
    request=None,
    requires_2fa=False,
    requires_2fa_setup=False,
    **kwargs,
):
    if requires_2fa_setup:
        action = "login.2fa_enrollment_required"
    elif requires_2fa:
        action = "login.2fa_required"
    else:
        action = "login.success"

    AuditService.record_on_commit(
        actor=user,
        category="AUTHENTICATION",
        action=action,
        status="success",
        request=request,
    )


@receiver(user_login_failed)
def audit_login_failure(
    sender,
    user=None,
    request=None,
    reason="Invalid credentials",
    **kwargs,
):
    AuditService.record(
        actor=user,
        category="AUTHENTICATION",
        action="login.failure",
        status="failure",
        reason=reason,
        request=request,
    )


@receiver(user_twofa_success)
def audit_twofa_success(sender, user, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=user,
        category="AUTHENTICATION",
        action="login.2fa_success",
        status="success",
        request=request,
    )


@receiver(user_twofa_failure)
def audit_twofa_failure(sender, user, request=None, **kwargs):
    AuditService.record(
        actor=user,
        category="AUTHENTICATION",
        action="login.2fa_failure",
        status="failure",
        request=request,
    )


@receiver(user_twofa_enabled)
def audit_twofa_enabled(sender, user, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=user,
        category="SECURITY",
        action="2fa.enable",
        resource=user,
        status="success",
        request=request,
    )


@receiver(user_twofa_reset)
def audit_twofa_reset(sender, user, actor=None, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=actor,
        category="SECURITY",
        action="2fa.reset",
        resource=user,
        status="success",
        request=request,
    )


@receiver(user_password_changed)
def audit_password_change(sender, user, actor=None, request=None, force=False, **kwargs):
    AuditService.record_on_commit(
        actor=actor or user,
        category="SECURITY",
        action="password.change",
        resource=user,
        status="success",
        request=request,
        metadata={"forced": bool(force)},
    )


@receiver(user_password_initialized)
def audit_password_initialized(sender, user, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=user,
        category="SECURITY",
        action="password.initialize",
        resource=user,
        status="success",
        request=request,
    )


@receiver(user_password_reset_requested)
def audit_password_reset_requested(
    sender,
    user,
    actor=None,
    purpose="self_service",
    request=None,
    **kwargs,
):
    AuditService.record_on_commit(
        actor=actor,
        category="SECURITY",
        action="password.reset_requested",
        resource=user,
        status="success",
        request=request,
        metadata={"purpose": purpose},
    )


@receiver(user_password_reset_completed)
def audit_password_reset_completed(
    sender,
    user,
    actor=None,
    purpose="self_service",
    request=None,
    **kwargs,
):
    AuditService.record_on_commit(
        actor=actor or user,
        category="SECURITY",
        action="password.reset_completed",
        resource=user,
        status="success",
        request=request,
        metadata={"purpose": purpose},
    )


@receiver(user_invitation_created)
def audit_invitation_created(sender, user, actor=None, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=actor,
        category="ADMINISTRATION",
        action="user.invitation_created",
        resource=user,
        status="success",
        request=request,
    )


@receiver(user_logout)
def audit_logout(sender, user=None, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=user,
        category="AUTHENTICATION",
        action="logout",
        status="success",
        request=request,
    )


@receiver(user_session_revoked)
def audit_session_revoke(
    sender,
    user,
    actor=None,
    session=None,
    request=None,
    reason="",
    **kwargs,
):
    if reason == "all_sessions":
        action = "session.revoke_all"
    elif reason == "refresh_token":
        action = "session.refresh_revoke"
    else:
        action = "session.revoke"

    AuditService.record_on_commit(
        actor=actor or user,
        category="SECURITY",
        action=action,
        resource=session or user,
        status="success",
        request=request,
    )


@receiver(user_deactivated)
def audit_deactivation(sender, user, actor=None, reason=None, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=actor,
        category="ADMINISTRATION",
        action="user.deactivate",
        resource=user,
        status="success",
        reason=reason or "",
        request=request,
    )


@receiver(user_reactivated)
def audit_reactivation(sender, user, actor=None, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=actor,
        category="ADMINISTRATION",
        action="user.reactivate",
        resource=user,
        status="success",
        request=request,
    )


@receiver(customer_created)
def audit_customer_created(sender, customer, actor=None, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=actor,
        category="BUSINESS",
        action="customer.create",
        resource=customer,
        status="success",
        request=request,
    )


@receiver(customer_updated)
def audit_customer_updated(sender, customer, actor=None, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=actor,
        category="BUSINESS",
        action="customer.update",
        resource=customer,
        status="success",
        request=request,
    )


@receiver(customer_activated)
def audit_customer_activated(sender, customer, actor=None, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=actor,
        category="BUSINESS",
        action="customer.activate",
        resource=customer,
        status="success",
        request=request,
    )


@receiver(customer_deactivated)
def audit_customer_deactivated(sender, customer, actor=None, request=None, **kwargs):
    AuditService.record_on_commit(
        actor=actor,
        category="BUSINESS",
        action="customer.deactivate",
        resource=customer,
        status="success",
        request=request,
    )


@receiver(portfolio_created)
def audit_portfolio_created(sender, portfolio, actor=None, **kwargs):
    AuditService.record(
        actor=actor,
        category="BUSINESS",
        action="portfolio.create",
        resource=portfolio,
        status="success",
    )


@receiver(portfolio_assigned)
def audit_portfolio_assigned(
    sender,
    portfolio,
    actor=None,
    from_commercial=None,
    to_commercial=None,
    reason=None,
    **kwargs,
):
    AuditService.record(
        actor=actor,
        category="ADMINISTRATION",
        action="portfolio.assign",
        resource=portfolio,
        status="success",
        reason=reason or "",
        metadata={
            "from_commercial_id": getattr(from_commercial, "pk", None),
            "to_commercial_id": getattr(to_commercial, "pk", None),
        },
    )


@receiver(portfolio_transferred)
def audit_portfolio_transferred(
    sender,
    portfolio,
    actor=None,
    to_commercial=None,
    reason=None,
    **kwargs,
):
    AuditService.record(
        actor=actor,
        category="ADMINISTRATION",
        action="portfolio.transfer",
        resource=portfolio,
        status="success",
        reason=reason or "",
        metadata={"to_commercial_id": getattr(to_commercial, "pk", None)},
    )


@receiver(credit_sale_status_changed)
def audit_credit_sale_status_changed(
    sender,
    sale,
    actor=None,
    previous_status="",
    new_status="",
    **kwargs,
):
    AuditService.record(
        actor=actor,
        category="BUSINESS",
        action="creditsale.status_change",
        resource=sale,
        status="success",
        metadata={
            "previous_status": previous_status,
            "new_status": new_status,
        },
    )


@receiver(recovery_created)
def audit_recovery_created(sender, recovery, actor=None, term=None, debt=None, **kwargs):
    AuditService.record(
        actor=actor,
        category="BUSINESS",
        action="recovery.create",
        resource=recovery,
        status="success",
        metadata={
            "term_id": getattr(term, "pk", None),
            "debt_id": getattr(debt, "pk", None),
            "amount": str(getattr(recovery, "amount", "")),
            "payment_mode": getattr(recovery, "payment_mode", ""),
        },
    )


@receiver(debt_status_updated)
def audit_debt_status_updated(sender, updated_debts=None, overdue_count=0, **kwargs):
    AuditService.record_on_commit(
        category="SYSTEM",
        action="debt.status_update",
        status="success",
        metadata={
            "overdue_count": overdue_count,
            "updated_count": len(updated_debts or []),
        },
    )
