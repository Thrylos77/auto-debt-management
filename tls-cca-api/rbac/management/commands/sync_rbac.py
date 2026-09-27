"""Synchronize declarative RBAC registry into the database."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from audit.services import AuditService
from rbac.models import Permission, Role
from rbac.registry.collector import collect_permissions, collect_roles


class Command(BaseCommand):
    help = "Synchronize permissions and roles from application registries."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--strict", action="store_true")
        parser.add_argument("--prune", action="store_true")
        parser.add_argument("--source", choices=["registry", "json"], default="registry")

    def handle(self, *args, **options):
        if options["source"] != "registry":
            raise CommandError("The JSON file is legacy/bootstrap only; use the registry source.")
        permissions = collect_permissions()
        roles = collect_roles()
        desired_codes = {p.code for p in permissions}

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY-RUN: no database changes will be made."))
            for definition in permissions:
                action = "create" if not Permission.objects.filter(code=definition.code).exists() else "sync"
                self.stdout.write(f"permission {action}: {definition.code}")
            for definition in roles:
                if definition.permissions != "ALL":
                    missing = sorted(set(definition.permissions) - desired_codes)
                    if missing:
                        raise CommandError(f"Role {definition.name} references unknown permissions: {missing}")
                action = "create" if not Role.objects.filter(name=definition.name).exists() else "sync"
                self.stdout.write(f"role {action}: {definition.name}")
            if options["prune"]:
                if not options["strict"]:
                    raise CommandError("--prune requires --strict because it deletes stale permissions.")
                stale = Permission.objects.filter(is_system=False).exclude(code__in=desired_codes).count()
                self.stdout.write(f"prune candidates: {stale} permission(s)")
            return

        with transaction.atomic():
            created_p = updated_p = created_r = updated_r = 0
            for definition in permissions:
                _, created = Permission.objects.update_or_create(
                    code=definition.code,
                    defaults={
                        "label": definition.label, "description": definition.description,
                        "namespace": definition.namespace or definition.code.split(".", 1)[0],
                        "is_system": definition.is_system,
                    },
                )
                created_p += int(created); updated_p += int(not created)
            for definition in roles:
                role, created = Role.objects.update_or_create(
                    name=definition.name,
                    defaults={
                        "description": definition.description, "is_system": definition.is_system,
                        "is_assignable": definition.is_assignable, "is_default": definition.is_default,
                        "managed_by_config": definition.managed_by_config,
                    },
                )
                wanted = Permission.objects.all() if definition.permissions == "ALL" else Permission.objects.filter(code__in=definition.permissions)
                found = set(wanted.values_list("code", flat=True))
                if definition.permissions != "ALL" and found != set(definition.permissions):
                    missing = sorted(set(definition.permissions) - found)
                    raise CommandError(f"Role {definition.name} references unknown permissions: {missing}")
                role.permissions.set(wanted)
                created_r += int(created); updated_r += int(not created)
            if options["prune"]:
                if not options["strict"]:
                    raise CommandError("--prune requires --strict because it deletes stale permissions.")
                deleted, _ = Permission.objects.filter(is_system=False).exclude(code__in=desired_codes).delete()
                self.stdout.write(self.style.WARNING(f"Pruned {deleted} stale permission row(s)."))
            AuditService.record(category="SYSTEM", action="rbac.sync", status="success", metadata={"permissions_created": created_p, "permissions_synchronized": updated_p, "roles_created": created_r, "roles_synchronized": updated_r})

        self.stdout.write(self.style.SUCCESS(f"Permissions: {created_p} created, {updated_p} synchronized"))
        self.stdout.write(self.style.SUCCESS(f"Roles: {created_r} created, {updated_r} synchronized"))
