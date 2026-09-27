from rbac.services.permission_resolver import PermissionResolver
class SessionPolicy:
    @staticmethod
    def can_list(actor, owner):
        return actor.pk == owner.pk

    @staticmethod
    def can_revoke(actor, session):
        return actor.pk == session.user_id or PermissionResolver.has(actor, "session.revoke")
