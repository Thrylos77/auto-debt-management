# Django command to automatically create a superuser from environment variables.
# Recommended usage: development, testing, CI/CD (never in production for security reasons).
# This command is automatically called when the server starts if DEBUG=True.
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

class Command(BaseCommand):
    help = "Create a superuser from environment variables"

    REQUIRED_ENV_VARS = [
        "SUPERUSER_USERNAME",
        "SUPERUSER_EMAIL",
        "SUPERUSER_PASSWORD",
        "SUPERUSER_FIRSTNAME",
        "SUPERUSER_LASTNAME",
        "SUPERUSER_BIRTHDAY",
    ]

    def handle(self, *args, **kwargs):
        User = get_user_model()

        # Check for required environment variables
        env = {var: os.environ.get(var) for var in self.REQUIRED_ENV_VARS}
        missing = [var for var, val in env.items() if not val]
        if missing:
            self.stdout.write('\n' + self.style.ERROR(f"❌ Missing environment variables: {', '.join(missing)}."))
            return

        if not User.objects.filter(username=env["SUPERUSER_USERNAME"]).exists():
            try:
                print("🛠️  Creating admin superuser...")
                User.objects.create_superuser(
                    username=env["SUPERUSER_USERNAME"],
                    email=env["SUPERUSER_EMAIL"],
                    password=env["SUPERUSER_PASSWORD"],
                    first_name=env["SUPERUSER_FIRSTNAME"],
                    last_name=env["SUPERUSER_LASTNAME"],
                    birthday=env["SUPERUSER_BIRTHDAY"],
                )
                self.stdout.write('\n' + self.style.SUCCESS("✔️  Superuser created successfully."))
            except IntegrityError as e:
                self.stdout.write('\n' + self.style.ERROR(f"❌ Error while creating superuser: {e}"))
        #else:
        #    self.stdout.write('\n' + self.style.WARNING("⚠️  Admin Superuser already exists."))

