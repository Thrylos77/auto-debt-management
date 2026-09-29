from rbac.services.permission_resolver import PermissionResolver


class UserPolicy:
    @staticmethod
    def can_view(actor, target):
        return (
            actor.is_superuser
            or actor.pk == target.pk
            or PermissionResolver.has(actor, "user.view")
        )

    @staticmethod
    def can_update(actor, target):
        return (
            actor.is_superuser
            or actor.pk == target.pk
            or PermissionResolver.has(actor, "user.update")
        )

    @staticmethod
    def can_deactivate(actor, target):
        return actor.is_superuser or PermissionResolver.has(
            actor,
            "user.deactivate",
        )

    @staticmethod
    def can_reactivate(actor, target):
        return actor.is_superuser or PermissionResolver.has(
            actor,
            "user.reactivate",
        )

    @staticmethod
    def can_change_password(actor, target):
        return actor.is_superuser or (
            actor.pk == target.pk
            and PermissionResolver.has(actor, "user.change_own_password")
        )
