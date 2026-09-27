from rbac.registry.collector import PermissionDefinition, RoleDefinition

PERMISSIONS = (
    PermissionDefinition(code='permission.list', label='List all permissions'),
    PermissionDefinition(code='permission.view', label='View a permission'),
    PermissionDefinition(code='permission.update', label='Update a permission'),
    PermissionDefinition(code='permission_history.view', label='View history of a permission'),
    PermissionDefinition(code='permission_history.list', label='List all permission histories'),
    PermissionDefinition(code='role.list', label='List all roles'),
    PermissionDefinition(code='role.create', label='Create a role'),
    PermissionDefinition(code='role.view', label='View a role'),
    PermissionDefinition(code='role.update', label='Update a role'),
    PermissionDefinition(code='role.delete', label='Delete a role'),
    PermissionDefinition(code='role_history.view', label='View history of a role'),
    PermissionDefinition(code='role_history.list', label='List all role histories'),
    PermissionDefinition(code='group.list', label='List all groups'),
    PermissionDefinition(code='group.create', label='Create a group'),
    PermissionDefinition(code='group.view', label='View a group'),
    PermissionDefinition(code='group.update', label='Update a group'),
    PermissionDefinition(code='group.delete', label='Delete a group'),
    PermissionDefinition(code='group_history.view', label='View history of a group'),
    PermissionDefinition(code='group_history.list', label='List all group histories'),
    PermissionDefinition(code='rbac.assign_role', label='Assign a role to a user'),
    PermissionDefinition(code='rbac.remove_role', label='Remove a role from a user'),
    PermissionDefinition(code='rbac.add_user_group', label='Add a user to a group'),
    PermissionDefinition(code='rbac.remove_user_group', label='Remove a user from a group'),
    PermissionDefinition(code='configuration.list', label='List configuration settings'),
    PermissionDefinition(code='configuration.view', label='View a configuration setting'),
    PermissionDefinition(code='configuration.update', label='Update a configuration setting'),
)

ROLES = (
    RoleDefinition(name='ADMIN', description='Grants all permissions in the system. For administrative use only.', permissions="ALL", is_system=True, is_assignable=False, is_default=False),
    RoleDefinition(name='COMMERCIAL', description='Default role for a new user. Can view and edit their own profile.', permissions=('user.view','user.update','user.change_own_password','user.request_otp','user.reset_password','customer.list','customer.view','customer.create','customer.update','portfolio.list','portfolio.view','creditsale.list','creditsale.view','creditsale.create','creditsale.update','debt.list','debt.view','term.list','term.view','recovery.list','recovery.view','recovery.create',), is_system=False, is_assignable=True, is_default=True),
    RoleDefinition(name='CONSULTANT', description='Can manage other users, including creating them and viewing the user list.', permissions=('user.list','user.view','user.update','user.create','user.change_own_password','user.request_otp','user.reset_password','rbac.add_user_group','rbac.remove_user_group','customer.list','customer.view','customer.list_all','portfolio.list','portfolio.view','creditsale.list','creditsale.view','debt.list','debt.view','term.list','term.view','recovery.list','recovery.view','reporting_dashboard.view','reporting_aging.view','reporting_evolution.view',), is_system=False, is_assignable=True, is_default=False),
    RoleDefinition(name='MODIFICATEUR', description='. Can view and edit their own profile.', permissions=('user.view','user.update','user.change_own_password','user.request_otp','user.reset_password','customer.list','customer.view','customer.list_all',), is_system=False, is_assignable=True, is_default=False),
)
