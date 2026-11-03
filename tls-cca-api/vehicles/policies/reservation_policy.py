"""Authorization and state rules for vehicle reservations."""

from rbac.services.permission_resolver import PermissionResolver

from vehicles.models import VehicleReservation, VehicleUnit


class ReservationPolicy:
    """Reservation authorization and basic business eligibility checks."""

    @staticmethod
    def _has(actor, code: str) -> bool:
        if actor is None:
            return True
        return bool(actor.is_superuser or PermissionResolver.has(actor, code))

    @classmethod
    def can_list(cls, actor):
        return cls._has(actor, "reservation.list")

    @classmethod
    def can_view(cls, actor, reservation=None):
        return cls._has(actor, "reservation.view")

    @classmethod
    def can_create_for_actor(cls, actor):
        """Check the RBAC grant separately from vehicle/customer eligibility."""
        return cls._has(actor, "reservation.create")

    @classmethod
    def can_create(cls, actor, vehicle, customer):
        if not cls.can_create_for_actor(actor):
            return False
        return bool(
            vehicle.status in {VehicleUnit.STATUS_IN_STOCK}
            and customer.is_active
        )

    @classmethod
    def can_release(cls, actor, reservation):
        return cls._has(actor, "reservation.release")

    @classmethod
    def can_expire(cls, actor, reservation=None):
        return cls._has(actor, "reservation.expire")

    @classmethod
    def can_convert_to_sale(cls, actor, reservation):
        if not cls._has(actor, "reservation.release"):
            return False
        return reservation.status == VehicleReservation.ACTIVE
