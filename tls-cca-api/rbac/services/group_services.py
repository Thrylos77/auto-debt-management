from rbac.models import Group

def create_group(name, description, roles):
    """Creates a new group with the given name, description, and roles."""
    group = Group.objects.create(name=name, description=description)
    group.roles.set(roles)
    return group

def update_group(group, name=None, description=None, roles=None):
    """Updates the given group with the provided data."""
    if name: group.name = name
    if description: group.description = description
    if roles is not None: group.roles.set(roles)