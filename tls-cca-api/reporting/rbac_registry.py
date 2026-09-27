from rbac.registry.collector import PermissionDefinition

PERMISSIONS = (
    PermissionDefinition(
        code='reporting_dashboard.view', label='View Global Dashboard'
    ),
    PermissionDefinition(
        code='reporting_aging.view', label='View Aging Balance Report'
    ),
    PermissionDefinition(
        code='reporting_evolution.view', label='View Recovery Evolution'
    ),
)
