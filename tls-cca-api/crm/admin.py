from django.contrib import admin
from .models import Customer, PhysicalPersonDetail, MoralPersonDetail, Portfolio

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

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_name', 'customer_type', 'email', 'phone', 'portfolio', 'created_at')
    search_fields = ('email', 'phone', 'physical_detail__first_name', 'physical_detail__last_name', 'moral_detail__business_name')
    list_filter = ('customer_type', 'portfolio')
    readonly_fields = ('created_at',)
    inlines = [PhysicalPersonDetailInline, MoralPersonDetailInline]

    # Ajout de JavaScript pour afficher/masquer les inlines dynamiquement
    class Media:
        js = ('crm/admin_customer.js',)

    def get_form(self, request, obj=None, **kwargs):
        # Assigner les classes CSS initiales au chargement de la page
        self.inlines[0].classes = ['collapse']
        self.inlines[1].classes = ['collapse']
        return super().get_form(request, obj, **kwargs)

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
    list_display = ('name', 'commercial', 'balance', 'active', 'created_at')
    search_fields = ('name', 'commercial__username', 'commercial__first_name', 'commercial__last_name')
    readonly_fields = ('created_at',)
