"""Identity model.

RBAC and the legacy TOTP fields remain temporarily for data migration compatibility.
New application code must use the dedicated security profile and the RBAC services.
"""

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
        """Compatibility accessor; PermissionResolver is the canonical implementation."""
        from rbac.services.permission_resolver import PermissionResolver
        return PermissionResolver.get_queryset(self)

    def has_permission(self, code: str) -> bool:
        from rbac.services.permission_resolver import PermissionResolver
        return PermissionResolver.has(self, code)

    def __str__(self):
        return f"{self.get_full_name()} {self.username}".strip()
