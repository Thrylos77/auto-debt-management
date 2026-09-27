"""Audit receivers for identity, session, and security domain events."""

from django.dispatch import receiver

from audit.services import AuditService
from users.events import (
    user_deactivated,
    user_login_failed,
    user_login_succeeded,
    user_logout,
    user_password_changed,
    user_reactivated,
    user_session_revoked,
    user_twofa_disabled,
    user_twofa_enabled,
    user_twofa_failure,
    user_twofa_success,
)


@receiver(user_login_succeeded)
def audit_login_success(
    sender,
    user,
    request=None,
    requires_2fa=False,
    **kwargs,
):
    AuditService.record_on_commit(
        actor=user,
        category="AUTHENTICATION",
        action=(
            "login.2fa_required"
            if requires_2fa
            else "login.success"
        ),
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
    # The authentication transaction has already completed before the event
    # is emitted. Record the failure immediately so the audit event is never
    # hidden behind an unrelated surrounding transaction.
    AuditService.record(
        actor=user,
        category="AUTHENTICATION",
        action="login.failure",
        status="failure",
        reason=reason,
        request=request,
    )


@receiver(user_twofa_success)
def audit_twofa_success(
    sender,
    user,
    recovery_code=False,
    request=None,
    **kwargs,
):
    AuditService.record_on_commit(
        actor=user,
        category="AUTHENTICATION",
        action=(
            "login.2fa_recovery"
            if recovery_code
            else "login.2fa_success"
        ),
        status="success",
        request=request,
    )


@receiver(user_twofa_failure)
def audit_twofa_failure(
    sender,
    user,
    request=None,
    **kwargs,
):
    # The invalid-attempt counter is committed before this signal is sent.
    # Persist the failure immediately for deterministic security auditing.
    AuditService.record(
        actor=user,
        category="AUTHENTICATION",
        action="login.2fa_failure",
        status="failure",
        request=request,
    )


@receiver(user_twofa_enabled)
def audit_twofa_enabled(
    sender,
    user,
    request=None,
    **kwargs,
):
    AuditService.record_on_commit(
        actor=user,
        category="SECURITY",
        action="2fa.enable",
        resource=user,
        status="success",
        request=request,
    )


@receiver(user_twofa_disabled)
def audit_twofa_disabled(
    sender,
    user,
    request=None,
    **kwargs,
):
    AuditService.record_on_commit(
        actor=user,
        category="SECURITY",
        action="2fa.disable",
        resource=user,
        status="success",
        request=request,
    )


@receiver(user_password_changed)
def audit_password_change(
    sender,
    user,
    actor=None,
    request=None,
    **kwargs,
):
    AuditService.record_on_commit(
        actor=actor or user,
        category="SECURITY",
        action="password.change",
        resource=user,
        status="success",
        request=request,
    )


@receiver(user_logout)
def audit_logout(
    sender,
    user=None,
    request=None,
    **kwargs,
):
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
def audit_deactivation(
    sender,
    user,
    actor=None,
    reason=None,
    request=None,
    **kwargs,
):
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
def audit_reactivation(
    sender,
    user,
    actor=None,
    request=None,
    **kwargs,
):
    AuditService.record_on_commit(
        actor=actor,
        category="ADMINISTRATION",
        action="user.reactivate",
        resource=user,
        status="success",
        request=request,
    )
