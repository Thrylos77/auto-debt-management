import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from rbac.models import Group, GroupMembership, Role, RoleAssignment

User = get_user_model()


@pytest.mark.django_db
def test_backfill_legacy_rbac_is_idempotent(capsys):
    user = User.objects.create_user(username="backfill-v2", email="backfill-v2@example.com", password="x")
    role = Role.objects.create(name="Backfill role")
    group = Group.objects.create(name="Backfill group")
    user.roles.add(role)
    user.groups.add(group)

    call_command("backfill_legacy_rbac")
    call_command("backfill_legacy_rbac")

    assert RoleAssignment.objects.filter(user=user, role=role).count() == 1
    assert GroupMembership.objects.filter(user=user, group=group).count() == 1
    output = capsys.readouterr().out
    assert "Backfill complete" in output
