"""Authorization rules for physical inventory sessions."""

from rbac.services.permission_resolver import PermissionResolver


class InventoryPolicy:
    """Keep inventory role decisions separate from workflow mechanics."""

    @staticmethod
    def _has(actor, code: str) -> bool:
        if actor is None:
            return True
        return bool(actor.is_superuser or PermissionResolver.has(actor, code))

    @classmethod
    def can_list(cls, actor):
        return cls._has(actor, "inventory.list")

    @classmethod
    def can_view(cls, actor, session=None):
        return cls._has(actor, "inventory.view")

    @classmethod
    def can_create(cls, actor):
        return cls._has(actor, "inventory.create")

    @classmethod
    def can_record(cls, actor, session=None):
        return cls._has(actor, "inventory.record")

    @classmethod
    def can_submit(cls, actor, session=None):
        return cls._has(actor, "inventory.submit")

    @classmethod
    def can_validate(cls, actor, session=None):
        return cls._has(actor, "inventory.validate")

    @classmethod
    def can_adjust(cls, actor, item=None):
        return cls._has(actor, "inventory.adjust")
