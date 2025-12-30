import pytest
from rbac.models import Permission, Role

@pytest.mark.django_db
def test_role_permission_assignment():
    """
    Test that a permission can be created and assigned to a role.
    """
    # 1. Create a Permission
    permission = Permission.objects.create(
        code="users.can_view_list",
        label="Can view user list"
    )
    assert str(permission) == "users.can_view_list"

    # 2. Create a Role
    role = Role.objects.create(name="Support Level 1")
    assert str(role) == "Support Level 1"

    # 3. Add the permission to the role
    role.permissions.add(permission)

    # 4. Assert that the role has the correct permission
    assert role.permissions.count() == 1
    assert role.permissions.first().code == "users.can_view_list"

    # Check the reverse relationship
    assert permission.roles.count() == 1
    assert permission.roles.first().name == "Support Level 1"
