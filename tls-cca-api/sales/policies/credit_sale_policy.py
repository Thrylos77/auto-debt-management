"""Authorization and segregation-of-duties policies for credit sales."""

from rbac.services.permission_resolver import PermissionResolver
from sales.models import CreditSaleStatus


class CreditSalePolicy:
    """Enforce status-transition authorization at the service boundary."""

    @staticmethod
    def can_change_status(actor, sale, new_status):
        if actor is None:
            return True
        if not actor.is_authenticated:
            return False
        if actor.is_superuser:
            return True
        if not PermissionResolver.has(actor, "creditsale.change_status"):
            return False
        if new_status in (CreditSaleStatus.APPROVED, CreditSaleStatus.REJECTED):
            return sale.commercial_id != actor.id
        return True
