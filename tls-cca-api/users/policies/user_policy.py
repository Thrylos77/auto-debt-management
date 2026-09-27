class UserPolicy:
    @staticmethod
    def can_view(actor, target):
        return actor.is_superuser or actor.pk == target.pk or actor.has_permission("user.view")

    @staticmethod
    def can_update(actor, target):
        return actor.is_superuser or actor.pk == target.pk or actor.has_permission("user.update")

    @staticmethod
    def can_deactivate(actor, target):
        return actor.is_superuser or actor.has_permission("user.delete")

    @staticmethod
    def can_reactivate(actor, target):
        return actor.is_superuser or actor.has_permission("user.reactivate")

    @staticmethod
    def can_change_password(actor, target):
        return actor.is_superuser or actor.pk == target.pk or actor.has_permission("user.change_password")
