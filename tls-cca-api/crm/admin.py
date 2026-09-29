from django.contrib import admin
from .models import Customer, CustomerAddress, PhysicalPersonDetail, MoralPersonDetail, Portfolio, PortfolioTransfer

# Les inlines permettent d'éditer les détails directement depuis la page Customer.
class PhysicalPersonDetailInline(admin.StackedInline):
    model = PhysicalPersonDetail
    can_delete = False
    verbose_name_plural = 'Physical Person Details'
    # Affiche l'inline seulement si le client est de type 'physical'
    # Cela nécessite un peu de JavaScript pour une expérience dynamique.
    classes = ('collapse', 'physical-inline')

class MoralPersonDetailInline(admin.StackedInline):
    model = MoralPersonDetail
    can_delete = False
    verbose_name_plural = 'Moral Person Details'
    classes = ('collapse', 'moral-inline')

class CustomerAddressInline(admin.TabularInline):
    model = CustomerAddress
    extra = 0
    fields = (
        'address_type',
        'label',
        'address_line_1',
        'address_line_2',
        'neighborhood',
        'city',
        'state_region',
        'postal_code',
        'country',
        'country_code',
        'is_primary',
    )

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'display_name',
        'customer_type',
        'lifecycle_status',
        'email',
        'phone',
        'portfolio',
        'created_at',
    )
    search_fields = (
        'email',
        'secondary_email',
        'phone',
        'mobile',
        'addresses__address_line_1',
        'addresses__neighborhood',
        'addresses__city',
        'addresses__country',
        'physical_detail__first_name',
        'physical_detail__middle_names',
        'physical_detail__last_name',
        'physical_detail__id_document_number',
        'moral_detail__business_name',
        'moral_detail__trading_name',
        'moral_detail__registration_number',
        'moral_detail__tax_identification_number',
    )
    list_filter = (
        'customer_type',
        'lifecycle_status',
        'preferred_contact_channel',
        'portfolio',
    )
    readonly_fields = (
        'created_at',
        'is_active',
        'lifecycle_status',
        'status_changed_at',
        'status_changed_by_id',
        'status_reason',
    )
    inlines = [CustomerAddressInline, PhysicalPersonDetailInline, MoralPersonDetailInline]

    # Ajout de JavaScript pour afficher/masquer les inlines dynamiquement
    class Media:
        js = ('crm/admin_customer.js',)

    def get_form(self, request, obj=None, **kwargs):
        # Assigner les classes CSS initiales au chargement de la page
        self.inlines[1].classes = ['collapse']
        self.inlines[2].classes = ['collapse']
        return super().get_form(request, obj, **kwargs)

@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = (
        'customer',
        'address_type',
        'neighborhood',
        'city',
        'country',
        'is_primary',
        'updated_at',
    )
    list_filter = ('address_type', 'country', 'is_primary')
    search_fields = (
        'customer__email',
        'customer__phone',
        'customer__physical_detail__first_name',
        'customer__physical_detail__last_name',
        'customer__moral_detail__business_name',
        'neighborhood',
        'city',
        'country',
    )

@admin.register(PhysicalPersonDetail)
class PhysicalPersonDetailAdmin(admin.ModelAdmin):
    list_display = ('customer', 'first_name', 'last_name', 'id_document_number')
    search_fields = ('first_name', 'last_name', 'id_document_number')

@admin.register(MoralPersonDetail)
class MoralPersonDetailAdmin(admin.ModelAdmin):
    list_display = ('customer', 'business_name', 'registration_number')
    search_fields = ('business_name', 'registration_number')

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('ref', 'commercial', 'balance', 'active', 'created_at')
    search_fields = ('ref', 'commercial__username', 'commercial__first_name', 'commercial__last_name')
    readonly_fields = ('created_at',)

@admin.register(PortfolioTransfer)
class PortfolioTransferAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'from_commercial', 'to_commercial', 'transferred_by', 'transferred_at')
    list_filter = ('transferred_at',)
    search_fields = ('portfolio__ref', 'from_commercial__username', 'to_commercial__username')
    readonly_fields = (
        'portfolio',
        'from_commercial',
        'to_commercial',
        'transferred_by',
        'reason',
        'transferred_at',
    )
    date_hierarchy = 'transferred_at'
