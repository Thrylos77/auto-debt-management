import pytest
from django.contrib.auth import get_user_model

from audit.models import AuditEvent
from audit.services import AuditService

User = get_user_model()

@pytest.mark.django_db
def test_sensitive_metadata_is_recursively_sanitized():
    user = User.objects.create_user(username="audit-v2", email="audit-v2@example.com", password="x")
    event = AuditService.record(actor=user, category="SECURITY", action="test", metadata={"password":"secret", "nested":{"refresh_token":"abc", "safe":"ok"}, "items":[{"authorization":"bearer"}]})
    assert event.metadata == {"password":"[REDACTED]", "nested":{"refresh_token":"[REDACTED]", "safe":"ok"}, "items":[{"authorization":"[REDACTED]"}]}

@pytest.mark.django_db
def test_audit_event_is_append_only():
    event = AuditEvent.objects.create(category="SYSTEM", action="test", status="success")
    with pytest.raises(RuntimeError): event.save()
    with pytest.raises(RuntimeError): event.delete()
    with pytest.raises(RuntimeError): AuditEvent.objects.filter(pk=event.pk).delete()

@pytest.mark.django_db
def test_audit_admin_disables_mutations():
    from django.contrib import admin
    from audit.admin import AuditEventAdmin
    model_admin = AuditEventAdmin(AuditEvent, admin.site)
    request = object()
    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)


@pytest.mark.django_db
def test_audit_queryset_update_is_blocked():
    event = AuditEvent.objects.create(category="SYSTEM", action="test-update", status="success")
    with pytest.raises(RuntimeError):
        AuditEvent.objects.filter(pk=event.pk).update(reason="changed")

@pytest.mark.django_db
def test_audit_actor_cannot_be_hard_deleted():
    user = User.objects.create_user(username="audit-protected", email="audit-protected@example.com", password="x")
    AuditService.record(actor=user, category="SECURITY", action="test", status="success")
    from django.db.models.deletion import ProtectedError
    with pytest.raises(ProtectedError):
        user.delete()

@pytest.mark.django_db(transaction=True)
def test_record_on_commit_persists_after_successful_transaction():
    from django.db import transaction

    with transaction.atomic():
        AuditService.record_on_commit(category="SYSTEM", action="commit.success", status="success")
        assert not AuditEvent.objects.filter(action="commit.success").exists()
    assert AuditEvent.objects.filter(action="commit.success").count() == 1


@pytest.mark.django_db(transaction=True)
def test_record_on_commit_is_discarded_when_transaction_rolls_back():
    from django.db import transaction

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            AuditService.record_on_commit(category="SYSTEM", action="commit.rollback", status="success")
            raise RuntimeError("force rollback")
    assert not AuditEvent.objects.filter(action="commit.rollback").exists()
