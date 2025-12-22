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

def desactivate_user(user):
    """
    Deactivates a user account.
    """
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