from rbac.registry.collector import PermissionDefinition

PERMISSIONS = (
    PermissionDefinition(
        code="dashboard.summary",
        label="View dashboard summary KPIs",
        description="View dashboard KPIs within the current authorization scope.",
    ),
    PermissionDefinition(
        code="dashboard.view_all_stats",
        label="View global dashboard statistics",
        description="View dashboard statistics across all authorized business data.",
    ),
    PermissionDefinition(
        code="reporting_dashboard.view",
        label="View global reporting dashboard",
    ),
    PermissionDefinition(
        code="reporting_aging.view",
        label="View aging balance report",
    ),
    PermissionDefinition(
        code="reporting_evolution.view",
        label="View recovery evolution",
    ),
)
