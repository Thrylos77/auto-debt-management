from rbac.registry.collector import PermissionDefinition

PERMISSIONS = (
    PermissionDefinition(
        code='user.list', label='List all users'
    ),
    PermissionDefinition(
        code='user.view', label='View a user'
    ),
    PermissionDefinition(
        code='user.create', label='Create a user'
    ),
    PermissionDefinition(
        code='user.update', label='Update a user'
    ),
    PermissionDefinition(
        code='user.deactivate', label='Deactivate a user (soft delete)'
    ),
    PermissionDefinition(
        code='user.change_own_password', label='Change own password'
    ),
    PermissionDefinition(
        code='user.reactivate', label='Reactivate a user'
    ),
    PermissionDefinition(
        code='user.change_password', label='Change password of any user'
    ),
    PermissionDefinition(
        code='user.request_otp', label='Request OTP for password reset'
    ),
    PermissionDefinition(
        code='user.reset_password', label='Reset password of any user'
    ),
    PermissionDefinition(
        code='user_history.view', label='View history of a user'
    ),
    PermissionDefinition(
        code='user_history.list', label='List all user histories'
    ),
    PermissionDefinition(
        code='user_roles.view', label='View roles of a user'
    ),
    PermissionDefinition(
        code='user_roles.update', label='Update roles of a user'
    ),
    PermissionDefinition(
        code='session.revoke', label='Revoke a user session'
    ),
)
