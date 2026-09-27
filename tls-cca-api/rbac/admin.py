from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Group, GroupMembership, Permission, Role, RoleAssignment

@admin.register(Permission)
class PermissionAdmin(SimpleHistoryAdmin):
    list_display = ("code", "label", "namespace", "is_system")
    list_filter = ("is_system", "namespace")
    search_fields = ("code", "label", "namespace")

@admin.register(Role)
class RoleAdmin(SimpleHistoryAdmin):
    list_display = ("name", "is_system", "is_assignable", "is_default", "managed_by_config")
    list_filter = ("is_system", "is_assignable", "is_default", "managed_by_config")
    search_fields = ("name", "description")
    filter_horizontal = ("permissions",)

@admin.register(Group)
class GroupAdmin(SimpleHistoryAdmin):
    list_display = ("name", "is_system")
    list_filter = ("is_system",)
    search_fields = ("name", "description")
    filter_horizontal = ("roles",)

@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "created_at", "created_by_id")
    search_fields = ("user__username", "user__email", "role__name")
    readonly_fields = tuple(field.name for field in RoleAssignment._meta.fields)

@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "group", "created_at", "created_by_id")
    search_fields = ("user__username", "user__email", "group__name")
    readonly_fields = tuple(field.name for field in GroupMembership._meta.fields)
