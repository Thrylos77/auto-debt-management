"""Authorization domain models.

The User.roles/User.groups relations remain only as a migration compatibility
layer; all new writes must use RoleAssignment/GroupMembership.
"""

from django.db import models
from simple_history.models import HistoricalRecords


class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    namespace = models.CharField(max_length=80, blank=True)
    is_system = models.BooleanField(default=False)
    history = HistoricalRecords(
        history_user_id_field=models.PositiveIntegerField(null=True, blank=True),
        history_change_reason_field=models.TextField(null=True),
    )

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["namespace", "code"], name="rbac_perm_ns_code_idx")]

    def save(self, *args, **kwargs):
        if not self.namespace and "." in self.code:
            self.namespace = self.code.split(".", 1)[0]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class Role(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)
    is_system = models.BooleanField(default=False)
    is_assignable = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    managed_by_config = models.BooleanField(default=False)
    history = HistoricalRecords(
        history_user_id_field=models.PositiveIntegerField(null=True, blank=True),
        history_change_reason_field=models.TextField(null=True),
    )

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_system", "is_assignable"], name="rbac_role_flags_idx")]

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    roles = models.ManyToManyField(Role, related_name="groups", blank=True)
    is_system = models.BooleanField(default=False)
    history = HistoricalRecords(
        history_user_id_field=models.PositiveIntegerField(null=True, blank=True),
        history_change_reason_field=models.TextField(null=True),
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RoleAssignment(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="role_assignments")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="assignments")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "role"], name="rbac_ra_user_role_uq")]
        indexes = [models.Index(fields=["user", "role"], name="rbac_ra_user_role_idx")]
        ordering = ["user_id", "role_id"]

    def __str__(self):
        return f"{self.user_id}:{self.role_id}"


class GroupMembership(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="group_memberships")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "group"], name="rbac_gm_user_group_uq")]
        indexes = [models.Index(fields=["user", "group"], name="rbac_gm_user_group_idx")]
        ordering = ["user_id", "group_id"]

    def __str__(self):
        return f"{self.user_id}:{self.group_id}"
