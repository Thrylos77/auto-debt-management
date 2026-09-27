from rbac.registry.collector import PermissionDefinition

PERMISSIONS = (
    PermissionDefinition(
        code="audit.list", label="List audit events", description="Read audit events."
    ),
    PermissionDefinition(
        code="audit.view", label="View an audit event", description="View one audit event."
    ),
)
