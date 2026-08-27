from rbac.models import Role

def create_role(name, description, permissions):
    """Creates a new role with the given name, description, and permissions."""
    role = Role.objects.create(name=name, description=description)
    role.permissions.set(permissions)
    return role

def update_role(role, name=None, description=None, permissions=None):
    """Updates the given role with the provided name, description, and permissions."""
    if name:
        role.name = name
    if description is not None:
        role.description = description
    if permissions is not None:
        role.permissions.set(permissions)
    role.save()
    return role
