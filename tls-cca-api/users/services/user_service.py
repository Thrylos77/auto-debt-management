"""User lifecycle services."""

from django.contrib.auth import get_user_model
from django.db import transaction

from core.events import user_deactivated, user_reactivated
from users.models import AccountStatus, UserSecurityProfile
from users.services import InvitationService

User = get_user_model()


@transaction.atomic
def create_user(validated_data, *, actor=None, request=None):
    """Create an invited user without setting a usable password."""
    user = User.objects.create_user(**validated_data)
    user.set_unusable_password()
    user.is_active = False
    user.account_status = AccountStatus.INVITED
    user.save(update_fields=["password", "is_active", "account_status"])
    InvitationService().issue(user, actor=actor, request=request)
    return user


def update_user(user, validated_data):
    for field, value in validated_data.items():
        setattr(user, field, value)
    user.save()
    return user


@transaction.atomic
def deactivate_user(
    user,
    *,
    successor_user=None,
    reason=None,
    actor=None,
    request=None,
):
    if not user.is_active and user.account_status == AccountStatus.DISABLED:
        return user

    user.is_active = False
    user.account_status = AccountStatus.DISABLED
    user.save(update_fields=["is_active", "account_status"])
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
    if user.account_status != AccountStatus.DISABLED and user.is_active:
        return user

    profile = UserSecurityProfile.objects.filter(user=user).first()
    if profile and profile.two_factor_enabled and user.has_usable_password():
        user.account_status = AccountStatus.ACTIVE
        user.is_active = True
    else:
        user.account_status = AccountStatus.PASSWORD_SET
        user.is_active = False
    user.save(update_fields=["account_status", "is_active"])
    user_reactivated.send(sender=User, user=user, actor=actor, request=request)
    return user


def get_accessible_users(actor):
    return User.objects.all().order_by("id")
