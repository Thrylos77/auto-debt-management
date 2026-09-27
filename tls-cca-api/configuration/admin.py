from django.contrib import admin

from configuration.models import SystemSetting


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "category",
        "value_type",
        "is_public",
        "updated_by",
        "updated_at",
    )
    search_fields = ("key", "category", "description")
    list_filter = ("category", "value_type", "is_public", "scope")
    readonly_fields = ("created_at", "updated_at")
