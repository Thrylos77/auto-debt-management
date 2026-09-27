from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from rbac.models import Role, RoleAssignment


class Command(BaseCommand):
    help = "Compatibility wrapper around sync_rbac and superuser assignment."

    def handle(self, *args, **options):
        call_command("sync_rbac")
        admin_role = Role.objects.filter(name="ADMIN").first()
        if admin_role:
            User = get_user_model()
            for user in User.objects.filter(is_superuser=True):
                RoleAssignment.objects.get_or_create(user=user, role=admin_role, defaults={"created_by_id": user.pk})
        self.stdout.write(self.style.SUCCESS("RBAC synchronization completed."))
