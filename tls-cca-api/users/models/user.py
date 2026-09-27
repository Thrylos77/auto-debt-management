"""Identity model.

RBAC and the legacy TOTP fields remain temporarily for data migration compatibility.
New application code must use the dedicated security profile and the RBAC services.
"""

from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from core.utils.validators import phone_validator


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    phone = models.CharField(max_length=30, blank=True, validators=[phone_validator])
    address = models.TextField(blank=True)
    birthday = models.DateField(blank=True, null=True)

    # Legacy RBAC relations. Do not use for new writes; Lot 2 migrates these away.
    roles = models.ManyToManyField("rbac.Role", related_name="users", blank=True)
    groups = models.ManyToManyField("rbac.Group", related_name="users", blank=True)

    # Legacy TOTP fields retained until the staged migration is complete.
    totp_secret = models.CharField(max_length=128, blank=True, null=True)
    is_2fa_enabled = models.BooleanField(default=False)

    history = HistoricalRecords(
        excluded_fields=["last_login"],
        history_change_reason_field=models.TextField(null=True),
    )

    REQUIRED_FIELDS = ["first_name", "last_name", "email"]

    @property
    def all_permissions(self):
        """Legacy permission accessor kept until PermissionResolver becomes canonical."""
        from rbac.services import permission_services

        return permission_services.get_user_permissions(self)

    def has_permission(self, code: str) -> bool:
        return self.is_superuser or self.all_permissions.filter(code=code).exists()

    def __str__(self):
        return f"{self.get_full_name()} {self.username}".strip()
