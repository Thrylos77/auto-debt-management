"""Authorization policy for recovery creation."""

from rbac.services.permission_resolver import PermissionResolver


class RecoveryPolicy:
    @staticmethod
    def can_create(actor):
        if actor is None:
            return True
        return bool(
            actor.is_superuser
            or (
                actor.is_authenticated
                and PermissionResolver.has(actor, "recovery.create")
            )
        )
