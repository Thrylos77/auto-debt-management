"""Transition registry kept deliberately free of product role names.

Lot 2 will move the authoritative declarations into ``rbac.registry``.
"""

DEFAULT_PROVISIONING_ROLE = None


def get_default_provisioning_role():
    """Return no role by default; product provisioning must decide explicitly."""
    return DEFAULT_PROVISIONING_ROLE
