from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import AccountInvitation, PasswordResetChallenge, TwoFAChallenge, TwoFASetup, UserSession


class Command(BaseCommand):
    help = "Remove expired security challenges and stale session records."

    def handle(self, *args, **options):
        now = timezone.now()
        invitation_count, _ = AccountInvitation.objects.filter(
            expires_at__lt=now,
            used_at__isnull=True,
        ).delete()
        reset_count, _ = PasswordResetChallenge.objects.filter(
            expires_at__lt=now,
            used_at__isnull=True,
        ).delete()
        challenge_count, _ = TwoFAChallenge.objects.filter(
            expires_at__lt=now,
            used_at__isnull=True,
        ).delete()
        setup_count, _ = TwoFASetup.objects.filter(
            expires_at__lt=now,
            used_at__isnull=True,
        ).delete()
        session_count, _ = UserSession.objects.filter(
            expires_at__lt=now,
            revoked_at__isnull=False,
        ).delete()
        self.stdout.write(
            self.style.SUCCESS(
                "Cleaned invitations={0}, password_resets={1}, "
                "2FA_challenges={2}, 2FA_setups={3}, revoked_sessions={4}.".format(
                    invitation_count,
                    reset_count,
                    challenge_count,
                    setup_count,
                    session_count,
                )
            )
        )
