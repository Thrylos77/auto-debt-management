"""Authorization rules for stock and physical locations."""

from rbac.services.permission_resolver import PermissionResolver


class StockPolicy:
    """Centralize stock-operation permissions."""

    @staticmethod
    def _has(actor, code: str) -> bool:
        if actor is None:
            return True
        return bool(actor.is_superuser or PermissionResolver.has(actor, code))

    @classmethod
    def can_list_location(cls, actor):
        return cls._has(actor, "stock.location.list")

    @classmethod
    def can_manage_location(cls, actor, location=None):
        return cls._has(actor, "stock.location.manage")

    @classmethod
    def can_view(cls, actor):
        return cls._has(actor, "stock.view")

    @classmethod
    def can_receive(cls, actor):
        return cls._has(actor, "stock.receive")

    @classmethod
    def can_transfer(cls, actor, vehicle=None):
        return cls._has(actor, "stock.transfer")

    @classmethod
    def can_adjust(cls, actor, vehicle=None):
        return cls._has(actor, "stock.adjust")
