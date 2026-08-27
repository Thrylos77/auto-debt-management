from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rbac.models import Role, Group
from django.contrib.auth import get_user_model

User = get_user_model()

def assign_role_to_user(user_id, role_id):
    """Assigns a role to a user."""
    user = get_object_or_404(User, pk=user_id)
    role = get_object_or_404(Role, pk=role_id)

    if user.roles.filter(pk=role.pk).exists():
        return Response(
            {"detail": "This user already has the specified role."},
            status=status.HTTP_400_BAD_REQUEST
        )
    user.roles.add(role)
    message = f"Role '{role.name}' assigned to user '{user.username}'."
    return Response({"detail": message}, status=status.HTTP_200_OK)

def remove_role_from_user(user_id, role_id):
    """Removes a role from a user."""
    user = get_object_or_404(User, pk=user_id)
    role = get_object_or_404(Role, pk=role_id)

    if not user.roles.filter(pk=role.pk).exists():
        return Response(
            {"detail": "This user does not have the specified role."},
            status=status.HTTP_400_BAD_REQUEST
        )
    user.roles.remove(role)
    message = f"Role '{role.name}' removed from user '{user.username}'."
    return Response({"detail": message}, status=status.HTTP_200_OK)

def add_user_to_group(group_id, user_ids):
    """Adds users to a group."""
    group = get_object_or_404(Group, pk=group_id)
    existing_ids = set(group.users.values_list('id', flat=True))
    added, skipped = [], []

    for user in User.objects.filter(id__in=user_ids):
        in_group = user.id in existing_ids
        if not in_group:
            group.users.add(user)
            added.append(user.username)
        else:
            skipped.append(user.username)

    status_code = 200 if added else 409
    message = f"Users added: {added}" if added else f"No users added; skipped: {skipped}"
    return Response({"detail": message}, status=status_code)


"""Removes users from a group."""
def remove_user_from_group(group_id, user_ids):
    group = get_object_or_404(Group, pk=group_id)
    existing_ids = set(group.users.values_list('id', flat=True))
    removed, skipped = [], []

    for user in User.objects.filter(id__in=user_ids):
        if user.id in existing_ids:
            group.users.remove(user)
            removed.append(user.username)
        else:
            skipped.append(user.username)

    status_code = 200 if removed else 409
    message = f"Users removed: {removed}" if removed else f"No users removed; skipped: {skipped}"
    return Response({"detail": message}, status=status_code)
