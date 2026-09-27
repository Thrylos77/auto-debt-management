from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import OTP, TwoFAChallenge, TwoFASetup, UserSession


class Command(BaseCommand):
    help = "Remove expired security challenges/OTPs and stale session records."

    def handle(self, *args, **options):
        now = timezone.now()
        otp_count, _ = OTP.objects.filter(expires_at__lt=now, is_used=False).delete()
        challenge_count, _ = TwoFAChallenge.objects.filter(expires_at__lt=now, used_at__isnull=True).delete()
        setup_count, _ = TwoFASetup.objects.filter(expires_at__lt=now, used_at__isnull=True).delete()
        session_count, _ = UserSession.objects.filter(expires_at__lt=now, revoked_at__isnull=False).delete()
        self.stdout.write(self.style.SUCCESS(
            f"Cleaned OTP={otp_count}, 2FA challenges={challenge_count}, "
            f"2FA setups={setup_count}, revoked sessions={session_count}."
        ))
