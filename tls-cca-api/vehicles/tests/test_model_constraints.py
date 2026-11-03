"""Regression tests for V07 model-level constraints and index naming."""

from vehicles.models import InventorySession, VehicleImage, VehicleReservation
from vehicles.models.catalog import (
    VehicleBrand,
    VehicleCategory,
    VehicleModel,
    VehicleVariant,
)
from vehicles.models.stock import StockLocation, StockMovement
from vehicles.models.vehicle import VehiclePriceHistory, VehicleUnit


MAX_SAFE_INDEX_NAME_LENGTH = 30


def _constraint(model, name):
    return next(
        constraint
        for constraint in model._meta.constraints
        if constraint.name == name
    )


def _vehicle_models():
    return (
        VehicleCategory,
        VehicleBrand,
        VehicleModel,
        VehicleVariant,
        StockLocation,
        VehicleUnit,
        VehicleImage,
        VehiclePriceHistory,
        StockMovement,
        VehicleReservation,
        InventorySession,
    )


def test_vehicle_reservation_active_constraint_uses_literal_status_value():
    constraint = _constraint(
        VehicleReservation,
        "vres_one_active_uq",
    )

    assert constraint.condition.children == [("status", "ACTIVE")]


def test_inventory_open_constraint_uses_literal_status_values():
    constraint = _constraint(
        InventorySession,
        "inv_one_open_location_uq",
    )

    assert constraint.condition.children == [
        ("status__in", ["DRAFT", "IN_PROGRESS", "SUBMITTED"])
    ]


def test_vehicle_explicit_index_and_constraint_names_fit_safe_database_limit():
    """Keep explicit V07 index and constraint names within a safe limit."""

    for model in _vehicle_models():
        for index in model._meta.indexes:
            assert len(index.name) <= MAX_SAFE_INDEX_NAME_LENGTH, (
                f"{model.__name__}.{index.name} exceeds "
                f"the {MAX_SAFE_INDEX_NAME_LENGTH}-character safe limit."
            )

        for constraint in model._meta.constraints:
            assert len(constraint.name) <= MAX_SAFE_INDEX_NAME_LENGTH, (
                f"{model.__name__}.{constraint.name} exceeds "
                f"the {MAX_SAFE_INDEX_NAME_LENGTH}-character safe limit."
            )
