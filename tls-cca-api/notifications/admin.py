from django.contrib import admin

from notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "category",
        "code",
        "is_read",
        "created_at",
    )
    list_filter = ("category", "is_read")
    search_fields = ("user__username", "user__email", "code", "title")
    readonly_fields = ("created_at", "read_at")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business_enabled",
        "marketing_enabled",
        "system_enabled",
        "updated_at",
    )
    search_fields = ("user__username", "user__email")


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "category", "channel", "is_active", "updated_at")
    list_filter = ("category", "channel", "is_active")
    search_fields = ("code", "subject")


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "notification",
        "channel",
        "status",
        "attempts",
        "sent_at",
    )
    list_filter = ("channel", "status")
    readonly_fields = ("created_at", "updated_at")
