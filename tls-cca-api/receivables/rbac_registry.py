from rbac.registry.collector import PermissionDefinition

PERMISSIONS = (
    PermissionDefinition(
        code='debt.list', label='List all debts'
    ),
    PermissionDefinition(
        code='debt.view', label='View a debt'
    ),
    PermissionDefinition(
        code='debt.create', label='Create a debt'
    ),
    PermissionDefinition(
        code='debt.update', label='Update a debt'
    ),
    PermissionDefinition(
        code='debt.delete', label='Delete a debt'
    ),
    PermissionDefinition(
        code='debt_history.view', label='View history of a debt'
    ),
    PermissionDefinition(
        code='debt_history.list', label='List all debt histories'
    ),
    PermissionDefinition(
        code='debt.update_status', label='Update debt and term statuses'
    ),
    PermissionDefinition(
        code='term.list', label='List all terms'
    ),
    PermissionDefinition(
        code='term.view', label='View a term'
    ),
    PermissionDefinition(
        code='term.create', label='Create a term'
    ),
    PermissionDefinition(
        code='term.update', label='Update a term'
    ),
    PermissionDefinition(
        code='term.delete', label='Delete a term'
    ),
    PermissionDefinition(
        code='term_history.view', label='View history of a term'
    ),
    PermissionDefinition(
        code='term_history.list', label='List all term histories'
    ),
    PermissionDefinition(
        code='recovery.list', label='List all recoveries'
    ),
    PermissionDefinition(
        code='recovery.view', label='View a recovery'
    ),
    PermissionDefinition(
        code='recovery.create', label='Create a recovery'
    ),
    PermissionDefinition(
        code='recovery.update', label='Update a recovery'
    ),
    PermissionDefinition(
        code='recovery.delete', label='Delete a recovery'
    ),
    PermissionDefinition(
        code='recovery_history.view', label='View history of a recovery'
    ),
    PermissionDefinition(
        code='recovery_history.list', label='List all recovery histories'
    ),
)
