"""Declarative RBAC permissions owned by the vehicles domain."""

from rbac.registry.collector import PermissionDefinition


PERMISSIONS = (
    PermissionDefinition("vehicle.list", "List vehicle units"),
    PermissionDefinition("vehicle.view", "View a vehicle unit"),
    PermissionDefinition("vehicle.create", "Create vehicle units and catalogue records"),
    PermissionDefinition("vehicle.update", "Update vehicle unit data"),
    PermissionDefinition("vehicle.change_price", "Change a vehicle price"),
    PermissionDefinition("vehicle.change_status", "Change operational vehicle status"),
    PermissionDefinition("vehicle.manage_images", "Add and manage vehicle images"),
    PermissionDefinition("vehicle.view_price_history", "View vehicle price history"),
    PermissionDefinition("vehicle.generate_qr", "Generate vehicle stock QR code"),
    PermissionDefinition("stock.location.list", "List stock locations"),
    PermissionDefinition("stock.location.manage", "Create or update stock locations"),
    PermissionDefinition("stock.view", "View stock movement history"),
    PermissionDefinition("stock.receive", "Receive a vehicle into stock"),
    PermissionDefinition("stock.transfer", "Transfer a vehicle between stock locations"),
    PermissionDefinition("stock.adjust", "Apply an explicit stock adjustment"),
    PermissionDefinition("reservation.list", "List vehicle reservations"),
    PermissionDefinition("reservation.view", "View a vehicle reservation"),
    PermissionDefinition("reservation.create", "Create a vehicle reservation"),
    PermissionDefinition("reservation.release", "Release a vehicle reservation"),
    PermissionDefinition("reservation.expire", "Expire due vehicle reservations"),
    PermissionDefinition("inventory.list", "List physical inventory sessions"),
    PermissionDefinition("inventory.view", "View a physical inventory session"),
    PermissionDefinition("inventory.create", "Create physical inventory sessions"),
    PermissionDefinition("inventory.record", "Record physical inventory observations"),
    PermissionDefinition("inventory.submit", "Submit a physical inventory session"),
    PermissionDefinition("inventory.validate", "Validate a physical inventory session"),
    PermissionDefinition("inventory.adjust", "Create an explicit stock adjustment from inventory"),
)
