"""V1 routes for vehicles, stock, reservations and physical inventory."""

from rest_framework.routers import DefaultRouter

from vehicles.views.catalog import (
    VehicleBrandViewSet,
    VehicleCategoryViewSet,
    VehicleModelViewSet,
    VehicleVariantViewSet,
)
from vehicles.views.inventory import InventorySessionViewSet
from vehicles.views.reservation import VehicleReservationViewSet
from vehicles.views.stock import StockLocationViewSet, StockMovementViewSet
from vehicles.views.vehicle import VehicleUnitViewSet


router = DefaultRouter()
router.register("categories", VehicleCategoryViewSet, basename="vehicle-category")
router.register("brands", VehicleBrandViewSet, basename="vehicle-brand")
router.register("models", VehicleModelViewSet, basename="vehicle-model")
router.register("variants", VehicleVariantViewSet, basename="vehicle-variant")
router.register("units", VehicleUnitViewSet, basename="vehicle-unit")
router.register("stock/locations", StockLocationViewSet, basename="stock-location")
router.register("stock/movements", StockMovementViewSet, basename="stock-movement")
router.register("reservations", VehicleReservationViewSet, basename="vehicle-reservation")
router.register("inventory", InventorySessionViewSet, basename="inventory-session")

urlpatterns = router.urls
