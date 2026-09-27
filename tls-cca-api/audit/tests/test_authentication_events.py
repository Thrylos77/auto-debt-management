import pytest
from django.contrib.auth import get_user_model

from audit.models import AuditEvent
from users.events import user_login_failed, user_twofa_failure

User = get_user_model()


@pytest.mark.django_db
def test_login_failure_audit_is_persisted_immediately():
    user = User.objects.create_user(
        username="audit-login-failure",
        email="audit-login-failure@example.com",
        password="x",
    )

    user_login_failed.send(
        sender=User,
        user=user,
        reason="Invalid credentials.",
    )

    assert AuditEvent.objects.filter(
        action="login.failure",
        status="failure",
        actor_user=user,
    ).exists()


@pytest.mark.django_db
def test_twofa_failure_audit_is_persisted_immediately():
    user = User.objects.create_user(
        username="audit-2fa-failure",
        email="audit-2fa-failure@example.com",
        password="x",
    )

    user_twofa_failure.send(
        sender=User,
        user=user,
    )

    assert AuditEvent.objects.filter(
        action="login.2fa_failure",
        status="failure",
        actor_user=user,
    ).exists()
