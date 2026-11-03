"""Administrative registration for the Vehicles & Inventory domain."""

from django.contrib import admin

from .models import (
    InventoryItem,
    InventorySession,
    StockLocation,
    StockMovement,
    VehicleBrand,
    VehicleCategory,
    VehicleImage,
    VehicleModel,
    VehiclePriceHistory,
    VehicleReservation,
    VehicleUnit,
    VehicleVariant,
)


@admin.register(VehicleCategory)
class VehicleCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "parent", "is_active", "sort_order")
    search_fields = ("code", "name")
    list_filter = ("is_active",)
    ordering = ("sort_order", "name")


@admin.register(VehicleBrand)
class VehicleBrandAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "created_at")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ("brand", "code", "name", "category", "is_active")
    search_fields = ("code", "name", "brand__code", "brand__name")
    list_filter = ("brand", "category", "is_active")
    autocomplete_fields = ("brand", "category")


@admin.register(VehicleVariant)
class VehicleVariantAdmin(admin.ModelAdmin):
    list_display = ("model", "code", "name", "fuel_type", "transmission", "is_active")
    search_fields = ("code", "name", "model__code", "model__name", "model__brand__name")
    list_filter = ("fuel_type", "transmission", "is_active")
    autocomplete_fields = ("model",)


class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 0
    fields = ("file", "is_primary", "sort_order", "caption", "mime_type", "file_size", "checksum", "uploaded_by", "uploaded_at")
    readonly_fields = ("mime_type", "file_size", "checksum", "uploaded_at")


@admin.register(VehicleUnit)
class VehicleUnitAdmin(admin.ModelAdmin):
    list_display = (
        "stock_reference",
        "variant",
        "color",
        "condition",
        "status",
        "current_location",
        "current_price",
        "currency",
    )
    search_fields = (
        "stock_reference",
        "vin",
        "chassis_number",
        "engine_number",
        "registration_number",
        "variant__name",
        "variant__model__name",
        "variant__model__brand__name",
    )
    list_filter = ("status", "condition", "mileage_unit", "currency", "is_catalog_visible")
    readonly_fields = ("stock_reference", "created_at", "updated_at")
    autocomplete_fields = ("variant", "current_location")
    inlines = (VehicleImageInline,)


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "is_primary", "sort_order", "mime_type", "file_size", "uploaded_by", "uploaded_at")
    search_fields = ("vehicle__stock_reference", "vehicle__vin", "checksum")
    list_filter = ("is_primary", "mime_type", "uploaded_at")
    readonly_fields = ("mime_type", "file_size", "checksum", "uploaded_at")
    autocomplete_fields = ("vehicle", "uploaded_by")


@admin.register(VehiclePriceHistory)
class VehiclePriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "old_price", "new_price", "currency", "reason", "changed_by", "changed_at")
    search_fields = ("vehicle__stock_reference", "vehicle__vin", "reason")
    list_filter = ("currency", "changed_at")
    readonly_fields = ("vehicle", "old_price", "new_price", "currency", "reason", "changed_by", "changed_at")
    autocomplete_fields = ("vehicle", "changed_by")


@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "type", "is_active", "created_at")
    search_fields = ("code", "name", "address")
    list_filter = ("type", "is_active")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "movement_type", "from_location", "to_location", "occurred_at", "performed_by")
    search_fields = ("vehicle__stock_reference", "vehicle__vin", "reference_id", "reason")
    list_filter = ("movement_type", "occurred_at")
    readonly_fields = (
        "vehicle",
        "movement_type",
        "from_location",
        "to_location",
        "reference_type",
        "reference_id",
        "reason",
        "performed_by",
        "occurred_at",
        "metadata",
    )
    autocomplete_fields = ("vehicle", "from_location", "to_location", "performed_by")


@admin.register(VehicleReservation)
class VehicleReservationAdmin(admin.ModelAdmin):
    list_display = ("reference", "vehicle", "customer", "status", "reserved_at", "expires_at", "reserved_by")
    search_fields = ("reference", "vehicle__stock_reference", "vehicle__vin", "customer__email")
    list_filter = ("status", "reserved_at", "expires_at")
    readonly_fields = ("reference", "reserved_at", "released_at", "released_by", "created_at", "updated_at")
    autocomplete_fields = ("vehicle", "customer", "reserved_by", "released_by")


@admin.register(InventorySession)
class InventorySessionAdmin(admin.ModelAdmin):
    list_display = ("reference", "location", "status", "started_at", "completed_at", "started_by", "validated_by")
    search_fields = ("reference", "location__code", "location__name")
    list_filter = ("status", "started_at", "completed_at")
    readonly_fields = ("reference", "created_at", "updated_at", "started_at", "completed_at")
    autocomplete_fields = ("location", "started_by", "validated_by")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("session", "vehicle", "scanned_reference", "found", "result", "observed_location", "observed_status")
    search_fields = ("session__reference", "vehicle__stock_reference", "scanned_reference")
    list_filter = ("found", "observed_status")
    autocomplete_fields = ("session", "vehicle", "expected_location", "observed_location", "scanned_by")
    readonly_fields = ("result", "scanned_at")
