"""Copy legacy User role/group M2Ms into the V2 assignment tables."""

from django.core.management.base import BaseCommand
from rbac.models import GroupMembership, RoleAssignment
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Backfill legacy User.roles/User.groups into RoleAssignment/GroupMembership."

    def handle(self, *args, **options):
        User = get_user_model()
        role_rows = 0
        group_rows = 0
        for user in User.objects.prefetch_related("roles", "groups").all().iterator(chunk_size=500):
            for role in user.roles.all():
                _, created = RoleAssignment.objects.get_or_create(user_id=user.pk, role_id=role.pk, defaults={"created_by_id": user.pk})
                role_rows += int(created)
            for group in user.groups.all():
                _, created = GroupMembership.objects.get_or_create(user_id=user.pk, group_id=group.pk, defaults={"created_by_id": user.pk})
                group_rows += int(created)
        self.stdout.write(self.style.SUCCESS(f"Backfill complete: {role_rows} role assignment(s), {group_rows} group membership(s)."))
