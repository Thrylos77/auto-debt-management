from django.conf import settings
from django.db import models
from django.utils import timezone


class UserSecurityProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_profile",
    )
    two_factor_enabled = models.BooleanField(default=False)
    totp_secret_encrypted = models.TextField(blank=True, null=True)
    last_two_factor_enrollment_at = models.DateTimeField(blank=True, null=True)
    last_password_change_at = models.DateTimeField(blank=True, null=True)
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(blank=True, null=True)
    last_security_event_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "User security profile"
        verbose_name_plural = "User security profiles"

    @property
    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > timezone.now())

    def __str__(self):
        return f"Security profile for {self.user}"


class TwoFASetup(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="twofa_setups")
    secret_encrypted = models.TextField()
    setup_token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"], name="users_2fasetup_u_created_idx")]


class TwoFAChallenge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="twofa_challenges")
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"], name="users_2fachal_u_created_idx")]

