from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    AccountInvitation,
    PasswordResetChallenge,
    TwoFAChallenge,
    TwoFASetup,
    User,
    UserPreference,
    UserSecurityProfile,
    UserSession,
)


@admin.register(User)
class CustomUserAdmin(SimpleHistoryAdmin, UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "account_status",
        "is_active",
        "is_staff",
    )
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("account_status", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Identity", {"fields": ("phone", "address", "birthday", "account_status")}),
    )


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "language",
        "timezone",
        "theme",
        "email_notifications",
        "system_notifications",
    )
    search_fields = ("user__username", "user__email")


@admin.register(UserSecurityProfile)
class UserSecurityProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "two_factor_enabled",
        "last_two_factor_enrollment_at",
        "failed_login_count",
        "locked_until",
        "last_password_change_at",
    )
    search_fields = ("user__username", "user__email")
    readonly_fields = ("totp_secret_encrypted",)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "created_at",
        "last_seen_at",
        "expires_at",
        "revoked_at",
        "jti",
    )
    list_filter = ("revoked_at",)
    search_fields = ("user__username", "jti", "device_name", "platform")
    readonly_fields = tuple(field.name for field in UserSession._meta.fields)


@admin.register(TwoFASetup)
class TwoFASetupAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "attempts", "used_at")
    readonly_fields = tuple(field.name for field in TwoFASetup._meta.fields)


@admin.register(TwoFAChallenge)
class TwoFAChallengeAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "attempts", "used_at")
    readonly_fields = tuple(field.name for field in TwoFAChallenge._meta.fields)


@admin.register(AccountInvitation)
class AccountInvitationAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "attempts", "used_at", "created_by")
    list_filter = ("used_at",)
    search_fields = ("user__username", "user__email")
    readonly_fields = tuple(field.name for field in AccountInvitation._meta.fields)


@admin.register(PasswordResetChallenge)
class PasswordResetChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "purpose",
        "created_at",
        "expires_at",
        "attempts",
        "used_at",
        "requested_by",
    )
    list_filter = ("purpose", "used_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = tuple(field.name for field in PasswordResetChallenge._meta.fields)
