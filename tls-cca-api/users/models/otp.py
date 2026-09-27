from django.contrib.auth.hashers import check_password
from django.conf import settings
from django.db import models
from django.utils import timezone


class OTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps")
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(blank=True, null=True)
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    EXPIRATION_MINUTES = 5
    MAX_ATTEMPTS = 5

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"], name="users_otp_user_created_idx")]

    def is_valid(self):
        return not self.is_used and self.attempts < self.MAX_ATTEMPTS and timezone.now() < self.expires_at

    def check_code(self, raw_code: str) -> bool:
        return check_password(raw_code, self.code_hash)

    def __str__(self):
        return f"OTP for {self.user} created at {self.created_at}"
