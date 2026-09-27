from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from users.models import User, UserSecurityProfile
from users.services.twofa_service import encrypt_secret


class Command(BaseCommand):
    help = "Encrypt legacy User.totp_secret values into UserSecurityProfile."

    @transaction.atomic
    def handle(self, *args, **options):
        migrated = 0
        for user in User.objects.exclude(totp_secret__isnull=True).exclude(totp_secret=""):
            profile, _ = UserSecurityProfile.objects.get_or_create(user=user)
            if not profile.totp_secret_encrypted:
                profile.totp_secret_encrypted = encrypt_secret(user.totp_secret)
                profile.two_factor_enabled = bool(user.is_2fa_enabled)
                profile.last_security_event_at = timezone.now()
                profile.save(update_fields=["totp_secret_encrypted", "two_factor_enabled", "last_security_event_at"])
            user.totp_secret = None
            user.save(update_fields=["totp_secret"])
            migrated += 1
        self.stdout.write(self.style.SUCCESS(f"Migrated {migrated} legacy TOTP secrets."))
