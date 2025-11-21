""" RBAC Models """
from django.db import models
from simple_history.models import HistoricalRecords

class Permission(models.Model):
    """
    Application-level permission (action/resource granularity).
    Example codes: "user.list", "user.create", "establishment.view_student"
    """
    code = models.CharField(max_length=50, unique=True)   # used by the code
    label = models.CharField(max_length=255, unique=True)  # human-readable
    description = models.TextField(blank=True)
    history = HistoricalRecords(
        # This will store the user's ID without creating a foreign key constraint,
        # breaking the circular dependency between 'users' and 'rbac' apps.
        history_user_id_field=models.PositiveIntegerField(null=True, blank=True),
    )

    class Meta:
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        ordering = ['code']

    def __str__(self):
        return self.code


class Role(models.Model):
    # Role = grouping of permissions
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, related_name='roles', blank=True)
    history = HistoricalRecords(
        history_user_id_field=models.PositiveIntegerField(null=True, blank=True),
    )
    
    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ['name']

    def __str__(self):
        return self.name

class Group(models.Model):
    """
    A group is a collection of users that can be assigned roles.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    roles = models.ManyToManyField('rbac.Role', related_name='groups', blank=True)
    history = HistoricalRecords(
        history_user_id_field=models.PositiveIntegerField(null=True, blank=True),
    )

    class Meta:
        verbose_name = "Group"
        verbose_name_plural = "Groups"
        ordering = ['name']

    def __str__(self):
        return self.name