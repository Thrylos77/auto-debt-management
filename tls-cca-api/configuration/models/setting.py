"""Persistent, typed application configuration."""

from django.conf import settings
from django.db import models


class SystemSetting(models.Model):
    """A typed, globally scoped setting managed by the configuration service."""

    SCOPE_GLOBAL = "GLOBAL"
    SCOPE_TENANT = "TENANT"
    SCOPE_USER = "USER"

    SCOPE_CHOICES = (
        (SCOPE_GLOBAL, "Global"),
        (SCOPE_TENANT, "Tenant"),
        (SCOPE_USER, "User"),
    )

    key = models.CharField(max_length=150)
    category = models.CharField(max_length=80)
    value = models.TextField()
    description = models.TextField(blank=True)
    value_type = models.CharField(max_length=20)
    is_public = models.BooleanField(default=False)
    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default=SCOPE_GLOBAL,
    )
    scope_ref = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_system_settings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System setting"
        verbose_name_plural = "System settings"
        ordering = ["category", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["key", "scope", "scope_ref"],
                name="configuration_setting_identity_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["category", "key"],
                name="config_setting_category_idx",
            ),
            models.Index(
                fields=["is_public", "key"],
                name="config_setting_public_idx",
            ),
        ]

    def __str__(self):
        return f"{self.key} = {self.value}"
