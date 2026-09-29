from django.conf import settings
from django.db import models


class AccountInvitation(models.Model):
    """One-time invitation used to initialize an invited account."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_invitations",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_account_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    MAX_ATTEMPTS = 5

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="users_invitation_user_idx",
            ),
        ]


class PasswordResetChallenge(models.Model):
    """Single-use, expiring password reset challenge."""

    SELF_SERVICE = "self_service"
    ADMIN_TRIGGERED = "admin_triggered"
    PURPOSE_CHOICES = (
        (SELF_SERVICE, "Self service"),
        (ADMIN_TRIGGERED, "Admin triggered"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_challenges",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(blank=True, null=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_password_resets",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    MAX_ATTEMPTS = 5

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "purpose", "created_at"],
                name="users_pwdreset_user_idx",
            ),
        ]
