from django.contrib import admin
from .models import Group, Role, Permission
from django.contrib.admin import ModelAdmin
from simple_history.admin import SimpleHistoryAdmin

@admin.register(Permission)
class PermissionAdmin(SimpleHistoryAdmin):
    list_display = ("code", "label")
    search_fields = ("code", "label")

@admin.register(Role)
class RoleAdmin(SimpleHistoryAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")
    filter_horizontal = ("permissions",)

@admin.register(Group)
class GroupAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")
    filter_horizontal = ("roles",)