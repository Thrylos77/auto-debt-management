from rbac.registry.collector import PermissionDefinition

PERMISSIONS = (
    PermissionDefinition(
        code='customer.list', label='List customers'
    ),
    PermissionDefinition(
        code='customer.view', label='View a customer'
    ),
    PermissionDefinition(
        code='customer.create', label='Create a customer'
    ),
    PermissionDefinition(
        code='customer.update', label='Update a customer'
    ),
    PermissionDefinition(
        code='customer.delete', label='Delete a customer'
    ),
    PermissionDefinition(
        code='customer.activate', label='Activate a customer'
    ),
    PermissionDefinition(
        code='customer.deactivate', label='Deactivate a customer'
    ),
    PermissionDefinition(
        code='customer.list_all', label='View all customers from all commercials'
    ),
    PermissionDefinition(
        code='customer_history.view', label='View history of a customer'
    ),
    PermissionDefinition(
        code='customer_history.list', label='List all customer histories'
    ),
    PermissionDefinition(
        code='customer.auto_customer_desactivation', label='Auto-deactivate inactive customers'
    ),
    PermissionDefinition(
        code='portfolio.list', label='List all portfolios'
    ),
    PermissionDefinition(
        code='portfolio.view', label='View a portfolio'
    ),
    PermissionDefinition(
        code='portfolio.create', label='Create a portfolio'
    ),
    PermissionDefinition(
        code='portfolio.update', label='Update a portfolio'
    ),
    PermissionDefinition(
        code='portfolio.delete', label='Delete a portfolio'
    ),
    PermissionDefinition(
        code='portfolio.assign', label='Assign a portfolio to a commercial'
    ),
    PermissionDefinition(
        code='portfolio.transfer', label='Transfer a portfolio to another commercial'
    ),
    PermissionDefinition(
        code='portfolio_history.view', label='View history of a portfolio'
    ),
    PermissionDefinition(
        code='portfolio_history.list', label='List all portfolio histories'
    ),
)
