from django.contrib.auth import get_user_model
from django.db import transaction

from users.events import user_deactivated, user_reactivated

User = get_user_model()


@transaction.atomic
def create_user(validated_data, *, actor=None):
    # roles/groups are intentionally rejected from the public serializer; keep this
    # guard for callers using the legacy service directly during migration.
    validated_data.pop("roles", None)
    validated_data.pop("groups", None)
    user = User.objects.create_user(**validated_data)
    return user


def update_user(user, validated_data):
    for field, value in validated_data.items():
        setattr(user, field, value)
    user.save()
    return user


@transaction.atomic
def deactivate_user(user, *, successor_user=None, reason=None, actor=None, request=None):
    if not user.is_active:
        return user
    user.is_active = False
    user.save(update_fields=["is_active"])
    user_deactivated.send(
        sender=User,
        user=user,
        successor_user=successor_user,
        reason=reason or "Account deactivated",
        actor=actor,
        request=request,
    )
    return user


def reactivate_user(user, *, actor=None, request=None):
    if user.is_active:
        return user
    user.is_active = True
    user.save(update_fields=["is_active"])
    user_reactivated.send(sender=User, user=user, actor=actor, request=request)
    return user


def get_accessible_users(actor):
    # Scope decisions stay in the authorization layer. Users no longer knows about
    # CRM roles such as COMMERCIAL.
    return User.objects.all().order_by("id")


# Compatibility aliases used by existing domain code.
def soft_delete_user(user, transfer_to=None, reason=None, transferred_by=None):
    return deactivate_user(
        user,
        successor_user=transfer_to,
        reason=reason,
        actor=transferred_by,
    )


def change_user_password(user, new_password, old_password=None):
    from .password_service import PasswordService

    return PasswordService().change_password(user, new_password, old_password=old_password)
