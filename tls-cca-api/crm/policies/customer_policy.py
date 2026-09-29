"""Authorization and scope rules for Customer operations."""

from rbac.services.permission_resolver import PermissionResolver


class CustomerPolicy:
    """Centralize customer action authorization and portfolio scope."""

    @staticmethod
    def has_scope(actor, customer):
        """Return whether the customer belongs to the actor's visible scope."""
        if actor is None:
            return True
        if actor.is_superuser or PermissionResolver.has(actor, "customer.list_all"):
            return True
        return customer.portfolio_id is not None and customer.portfolio.commercial_id == actor.id

    @staticmethod
    def can_transition(actor, customer, permission_code):
        """Authorize a lifecycle transition and enforce object scope."""
        if actor is None:
            return True
        if not PermissionResolver.has(actor, permission_code):
            return False
        return CustomerPolicy.has_scope(actor, customer)

    @staticmethod
    def can_view_timeline(actor, customer):
        """Authorize timeline access for a customer in the actor's scope."""
        if actor is None:
            return True
        if not PermissionResolver.has(actor, "customer.timeline"):
            return False
        return CustomerPolicy.has_scope(actor, customer)
