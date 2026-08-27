""" users/services/user_services.py """

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from users.models import User
from rbac.models import Role

def create_user(validated_data):
    """
    Creates a user, assigns a default 'USER' role if none is provided,
    and handles M2M relationships for roles and groups.
    """
    roles = validated_data.pop('roles', [])
    groups = validated_data.pop('groups', [])
    user = User.objects.create_user(**validated_data)

    if not roles:
        try:
            default_role = Role.objects.get(name="COMMERCIAL")
            roles = [default_role]
        except Role.DoesNotExist:
            roles = []  # Or handle as an error
            
    user.groups.set(groups)
    user.roles.set(roles)
    return user

def change_user_password(user, new_password, old_password=None):
    """
    Changes a user's password. If old_password is provided, it will be
    validated against the user's current password.
    """
    if old_password:
        if not user.check_password(old_password):
            raise serializers.ValidationError({"old_password": "Incorrect old password."})
    
    if user.check_password(new_password):
        raise serializers.ValidationError("The new password must be different from the old password.")
    
    validate_password(new_password, user=user)
    user.set_password(new_password)
    user.save()
    return user

def soft_delete_user(user, transfer_to=None, reason=None, transferred_by=None):
    """
    Soft delete a user account (deactivation).

    If `transfer_to` is an active commercial, all of `user`'s active portfolios
    are automatically transferred to `transfer_to` BEFORE the account is
    deactivated (the "leaving commercial" scenario).
    """
    if transfer_to is not None:
        # Imported inside to avoid a circular import at module load time.
        from crm.services.portfolio_services import transfer_active_portfolios_of_commercial
        transfer_active_portfolios_of_commercial(
            from_commercial=user,
            to_commercial=transfer_to,
            transferred_by=transferred_by or user,
            reason=reason or f"Leaving commercial '{user}' deactivated",
        )

    user.is_active = False
    user.save()
    return user

def reactivate_user(user):
    """
    Activates a user account.
    """
    user.is_active = True
    user.save()
    return user

def get_accessible_users(user):
    """
    Returns the queryset of users visible to the requesting user.
    - Admins/Superusers (with user.create) see everyone.
    - Others (with just user.list) see only Commercials.
    """
    if user.is_superuser or user.has_permission('user.create'):
        return User.objects.all()
    
    return User.objects.filter(roles__name='COMMERCIAL')
