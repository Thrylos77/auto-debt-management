from django.conf import settings
from django.db import models
from django.utils import timezone


class UserSecurityProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="security_profile")
    two_factor_enabled = models.BooleanField(default=False)
    totp_secret_encrypted = models.TextField(blank=True, null=True)
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
