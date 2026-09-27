from rbac.registry.collector import PermissionDefinition

PERMISSIONS = (
    PermissionDefinition(
        code='creditsale.list', label='List all credit sales'
    ),
    PermissionDefinition(
        code='creditsale.view', label='View a credit sale'
    ),
    PermissionDefinition(
        code='creditsale.create', label='Create a credit sale'
    ),
    PermissionDefinition(
        code='creditsale.update', label='Update a credit sale'
    ),
    PermissionDefinition(
        code='creditsale.delete', label='Delete a credit sale'
    ),
    PermissionDefinition(
        code='creditsale.list_all', label='List all credit sales from all commercials'
    ),
    PermissionDefinition(
        code='creditsale.change_status', label='Approve or reject (change status of) a credit sale'
    ),
    PermissionDefinition(
        code='creditsale_history.view', label='View history of a credit sale'
    ),
    PermissionDefinition(
        code='creditsale_history.list', label='List all credit sale histories'
    ),
)
