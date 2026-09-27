from django.contrib import admin
from .models import AuditEvent

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "category", "action", "status", "actor_user", "resource_type", "resource_id")
    list_filter = ("category", "status", "action")
    search_fields = ("correlation_id", "resource_id", "actor_user__username", "actor_user__email")
    readonly_fields = tuple(field.name for field in AuditEvent._meta.fields)
    actions = ()

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
