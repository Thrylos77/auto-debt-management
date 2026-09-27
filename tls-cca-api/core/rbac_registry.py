from rbac.registry.collector import PermissionDefinition

PERMISSIONS = (
    PermissionDefinition(code='dashboard.summary', label='View dashboard summary KPIs'),
    PermissionDefinition(code='dashboard.view_all_stats', label='View global dashboard statistics'),
)
