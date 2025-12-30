"""
Management command to seed roles and permissions from a JSON configuration file.
This command reads a JSON file containing roles and permissions, 
creates them in the database, and assigns them to the appropriate users.
"""
import json
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rbac.models import Role, Permission

class Command(BaseCommand):
    help = "Seed roles and permissions from JSON config"

    def handle(self, *args, **options):
        # Charger le fichier JSON
        config_path = os.path.join('rbac', 'fixtures', 'permissions_config.json')
        if not os.path.exists(config_path):
            self.stdout.write(self.style.ERROR(f"Config file not found: {config_path}"))
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 1. Créer les permissions
        self.stdout.write("\n--- Seeding Permissions ---")
        for perm_data in config.get("permissions", []):
            perm, created = Permission.objects.get_or_create(
                code=perm_data["code"],
                defaults={
                    "label": perm_data.get("label", perm_data["code"]),
                    "description": perm_data.get("description", "")
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✔️  Permission '{perm.code}' created."))
            #else:
            #    self.stdout.write(self.style.WARNING(f"⚠️  Permission '{perm.code}' already exists."))

        # 2. Create/Update roles and assign permissions
        self.stdout.write("\n--- Seeding Roles and Assigning Permissions ---")
        for role_data in config.get("roles", []):
            role_name = role_data["name"]
            role_description = role_data.get("description", "")
            perm_codes = role_data["permissions"]

            # Get or create the role, and only update if necessary
            try:
                role = Role.objects.get(name=role_name)
                if role.description != role_description:
                    role.description = role_description
                    role.save(update_fields=['description'])
                    self.stdout.write(self.style.SUCCESS(f"✔️  Role '{role_name}' description updated."))
                #else:
                #    self.stdout.write(self.style.WARNING(f"⚠️  Role '{role_name}' already exists and is up-to-date."))
            except Role.DoesNotExist:
                role = Role.objects.create(name=role_name, description=role_description)
                self.stdout.write(self.style.SUCCESS(f"✔️  Role '{role_name}' created."))

            # Assign permissions to the role intelligently
            target_perms_qs = Permission.objects.all() if perm_codes == "ALL" else Permission.objects.filter(code__in=perm_codes)
            
            current_perm_ids = set(role.permissions.values_list('id', flat=True))
            target_perm_ids = set(target_perms_qs.values_list('id', flat=True))

            if current_perm_ids != target_perm_ids:
                role.permissions.set(target_perms_qs)
                self.stdout.write(self.style.SUCCESS(
                    f"✔️  Permissions for '{role_name}' set to: {list(target_perms_qs.values_list('code', flat=True))}"
                ))

        # 3. Assign ADMIN role to superusers
        self.stdout.write("\n--- Assigning ADMIN Role to Superusers ---")
        User = get_user_model()
        try:
            admin_role = Role.objects.get(name="ADMIN")
            for su in User.objects.filter(is_superuser=True):
                if not su.roles.filter(pk=admin_role.pk).exists():
                    su.roles.add(admin_role)
                    self.stdout.write(self.style.SUCCESS(f"✔️  Superuser '{su.username}' assigned to role ADMIN."))
                #else:
                #    self.stdout.write(self.style.WARNING(f"⚠️  Superuser '{su.username}' already has role ADMIN."))
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Role 'ADMIN' not found in DB. Cannot assign to superusers."))

        self.stdout.write(self.style.SUCCESS("\n✅ RBAC seeding completed."))
