class TwoFAPolicy:
    @staticmethod
    def can_manage(actor, target):
        return actor.pk == target.pk
