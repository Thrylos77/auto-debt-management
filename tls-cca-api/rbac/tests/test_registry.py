import pytest
from io import StringIO
from django.core.management import call_command

from audit.models import AuditEvent
from rbac.models import Permission, Role
from rbac.registry.collector import collect_permissions

@pytest.mark.django_db
def test_registry_has_unique_codes_and_audit_permissions():
    definitions = collect_permissions()
    codes = [item.code for item in definitions]
    assert len(codes) == len(set(codes))
    assert "audit.list" in codes
    assert "permission.list" in codes
    assert len(codes) == len(set(codes))

@pytest.mark.django_db
def test_sync_rbac_dry_run_does_not_write():
    output = StringIO()
    call_command("sync_rbac", "--dry-run", stdout=output)
    assert Permission.objects.count() == 0
    assert Role.objects.count() == 0
    assert AuditEvent.objects.count() == 0
    assert "DRY-RUN" in output.getvalue()


@pytest.mark.django_db
def test_sync_rbac_dry_run_validates_role_references():
    from unittest.mock import patch
    from django.core.management.base import CommandError
    from rbac.registry.collector import RoleDefinition

    bad = RoleDefinition(name="BROKEN", description="broken", permissions=("missing.permission",))
    with patch("rbac.management.commands.sync_rbac.collect_roles", return_value=(bad,)):
        with pytest.raises(CommandError, match="missing.permission"):
            call_command("sync_rbac", "--dry-run", "--strict")
