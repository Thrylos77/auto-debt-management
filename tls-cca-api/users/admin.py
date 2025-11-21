from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

from simple_history.admin import SimpleHistoryAdmin
# Import the token models from simplejwt
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
admin.site.unregister(OutstandingToken)
admin.site.unregister(BlacklistedToken)


@admin.register(User)
class CustomUserAdmin(SimpleHistoryAdmin, UserAdmin):
    # Customize the fields displayed in the user list
    list_display = ('username', 'email', 'first_name', 'last_name', 'birthday', 'is_staff', '_roles', '_groups')

    def _roles(self, obj):
        return ", ".join([role.name for role in obj.roles.all()])
    _roles.short_description = 'Roles'

    def _groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])
    _groups.short_description = 'Groups'

    def get_queryset(self, request):
        # Optimization to avoid N+1 problem
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('roles', 'groups')

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('RBAC', {'fields': ('roles',)}),
    )



# This code registers the AuditLog model with the Django admin interface.
# It customizes the admin display for AuditLog entries:
# - Shows columns: timestamp, user, action, and details in the list view.
# - Allows filtering logs by action and user.
# - Enables searching logs by the username of the user and the details field.
@admin.register(OutstandingToken)
class OutstandingTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'jti', 'created_at', 'expires_at')
    list_select_related = ('user',)
    search_fields = ('user__username', 'jti')
    ordering = ('-created_at',)

@admin.register(BlacklistedToken)
class BlacklistedTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user', 'get_jti', 'blacklisted_at')
    search_fields = ('token__user__username', 'token__jti')
    ordering = ('-blacklisted_at',)

    @admin.display(description='User', ordering='token__user')
    def get_user(self, obj):
        return obj.token.user

    @admin.display(description='JTI (JWT ID)', ordering='token__jti')
    def get_jti(self, obj):
        return obj.token.jti