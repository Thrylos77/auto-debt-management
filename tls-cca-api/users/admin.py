from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import RecoveryCode, TwoFAChallenge, TwoFASetup, User, UserPreference, UserSecurityProfile, UserSession


@admin.register(User)
class CustomUserAdmin(SimpleHistoryAdmin, UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_active", "is_staff", "is_2fa_enabled")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = UserAdmin.fieldsets + (
        ("Identity", {"fields": ("phone", "address", "birthday")}),
        ("Legacy migration", {"fields": ("roles", "totp_secret", "is_2fa_enabled")}),
    )


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "language", "timezone", "theme", "email_notifications", "system_notifications")
    search_fields = ("user__username", "user__email")


@admin.register(UserSecurityProfile)
class UserSecurityProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "two_factor_enabled", "failed_login_count", "locked_until", "last_password_change_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("totp_secret_encrypted",)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "last_seen_at", "expires_at", "revoked_at", "jti")
    list_filter = ("revoked_at",)
    search_fields = ("user__username", "jti", "device_name", "platform")
    readonly_fields = tuple(field.name for field in UserSession._meta.fields)


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "used_at", "revoked_at")
    readonly_fields = tuple(field.name for field in RecoveryCode._meta.fields)


@admin.register(TwoFASetup)
class TwoFASetupAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "attempts", "used_at")
    readonly_fields = tuple(field.name for field in TwoFASetup._meta.fields)


@admin.register(TwoFAChallenge)
class TwoFAChallengeAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "attempts", "used_at")
    readonly_fields = tuple(field.name for field in TwoFAChallenge._meta.fields)
