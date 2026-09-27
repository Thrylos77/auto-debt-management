from rbac.registry.collector import PermissionDefinition


PERMISSIONS = (
    PermissionDefinition(
        code="configuration.list",
        label="List configuration settings",
    ),
    PermissionDefinition(
        code="configuration.view",
        label="View a configuration setting",
    ),
    PermissionDefinition(
        code="configuration.update",
        label="Update a configuration setting",
    ),
)
