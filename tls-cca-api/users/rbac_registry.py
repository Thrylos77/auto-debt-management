"""User-domain permissions."""

from rbac.registry.collector import PermissionDefinition


PERMISSIONS = (
    PermissionDefinition(
        code="user.list",
        label="List all users",
    ),
    PermissionDefinition(
        code="user.view",
        label="View a user",
    ),
    PermissionDefinition(
        code="user.create",
        label="Create a user",
    ),
    PermissionDefinition(
        code="user.invite",
        label="Send or resend a user invitation",
    ),
    PermissionDefinition(
        code="user.update",
        label="Update a user",
    ),
    PermissionDefinition(
        code="user.deactivate",
        label="Deactivate a user",
    ),
    PermissionDefinition(
        code="user.change_own_password",
        label="Change own password",
    ),
    PermissionDefinition(
        code="user.reactivate",
        label="Reactivate a user",
    ),
    PermissionDefinition(
        code="user.security.reset_password",
        label="Trigger a secure password reset for another user",
    ),
    PermissionDefinition(
        code="user.security.reset_2fa",
        label="Reset another user's Authenticator",
    ),
    PermissionDefinition(
        code="user_history.view",
        label="View history of a user",
    ),
    PermissionDefinition(
        code="user_history.list",
        label="List all user histories",
    ),
    PermissionDefinition(
        code="user_roles.view",
        label="View roles of a user",
    ),
    PermissionDefinition(
        code="user_roles.update",
        label="Update roles of a user",
    ),
    PermissionDefinition(
        code="session.revoke",
        label="Revoke a user session",
    ),
)
