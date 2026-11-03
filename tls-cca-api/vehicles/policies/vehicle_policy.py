"""Authorization rules for physical vehicle units."""

from rbac.services.permission_resolver import PermissionResolver


class VehiclePolicy:
    """Keep vehicle authorization independent from DRF views and serializers."""

    @staticmethod
    def _has(actor, code: str) -> bool:
        if actor is None:
            return True
        return bool(actor.is_superuser or PermissionResolver.has(actor, code))

    @classmethod
    def can_list(cls, actor):
        return cls._has(actor, "vehicle.list")

    @classmethod
    def can_view(cls, actor, vehicle=None):
        return cls._has(actor, "vehicle.view")

    @classmethod
    def can_create(cls, actor):
        return cls._has(actor, "vehicle.create")

    @classmethod
    def can_update(cls, actor, vehicle):
        return cls._has(actor, "vehicle.update")

    @classmethod
    def can_change_price(cls, actor, vehicle):
        return cls._has(actor, "vehicle.change_price")

    @classmethod
    def can_change_status(cls, actor, vehicle):
        return cls._has(actor, "vehicle.change_status")

    @classmethod
    def can_manage_images(cls, actor, vehicle):
        return cls._has(actor, "vehicle.manage_images")

    @classmethod
    def can_view_price_history(cls, actor, vehicle):
        return cls._has(actor, "vehicle.view_price_history")

    @classmethod
    def can_generate_qr(cls, actor, vehicle):
        return cls._has(actor, "vehicle.generate_qr")
