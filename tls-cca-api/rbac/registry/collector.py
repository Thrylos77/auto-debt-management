"""Collect declarative permission definitions from installed applications."""

from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    label: str
    description: str = ""
    namespace: str = ""
    is_system: bool = False


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    description: str
    permissions: tuple[str, ...] | str
    is_system: bool = False
    is_assignable: bool = True
    is_default: bool = False
    managed_by_config: bool = True


APP_REGISTRIES = (
    "rbac.rbac_registry",
    "users.rbac_registry",
    "core.rbac_registry",
    "crm.rbac_registry",
    "sales.rbac_registry",
    "receivables.rbac_registry",
    "reporting.rbac_registry",
    "audit.rbac_registry",
    "configuration.rbac_registry",
)


def collect_permissions():
    collected = {}
    for module_name in APP_REGISTRIES:
        module = import_module(module_name)
        for definition in getattr(module, "PERMISSIONS", ()):
            existing = collected.get(definition.code)
            if existing and existing != definition:
                raise ValueError(f"Duplicate permission definition: {definition.code}")
            collected[definition.code] = definition
    return tuple(sorted(collected.values(), key=lambda item: item.code))


def collect_roles():
    return tuple(import_module("rbac.rbac_registry").ROLES)
