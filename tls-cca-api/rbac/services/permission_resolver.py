"""Single canonical permission resolution point."""

from django.db.models import Q

from rbac.models import Permission


class PermissionResolver:
    @staticmethod
    def get_queryset(user):
        if not user or not getattr(user, "is_authenticated", False):
            return Permission.objects.none()
        if user.is_superuser:
            return Permission.objects.all()

        return Permission.objects.filter(
            Q(roles__assignments__user=user)
            | Q(roles__groups__memberships__user=user)
        ).distinct()

    @classmethod
    def get_codes(cls, user):
        return set(cls.get_queryset(user).values_list("code", flat=True))

    @classmethod
    def has(cls, user, code):
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if user.is_superuser:
            return True
        return cls.get_queryset(user).filter(code=code).exists()
