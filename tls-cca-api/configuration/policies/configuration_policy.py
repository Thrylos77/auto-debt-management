"""Authorization rules specific to platform configuration."""

from rbac.services.permission_resolver import PermissionResolver


class ConfigurationPolicy:
    """Centralize configuration authorization instead of embedding it in views."""

    @staticmethod
    def can_list(actor) -> bool:
        return bool(
            actor
            and actor.is_authenticated
            and PermissionResolver.has(actor, "configuration.list")
        )

    @staticmethod
    def can_view(actor, setting=None) -> bool:
        return bool(
            actor
            and actor.is_authenticated
            and (
                PermissionResolver.has(actor, "configuration.view")
                or PermissionResolver.has(actor, "configuration.list")
            )
        )

    @staticmethod
    def can_update(actor, setting=None) -> bool:
        return bool(
            actor
            and actor.is_authenticated
            and PermissionResolver.has(actor, "configuration.update")
        )
