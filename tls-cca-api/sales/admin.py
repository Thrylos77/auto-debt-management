from django.contrib import admin
from .models import CreditSale

@admin.register(CreditSale)
class CreditSaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'commercial', 'portfolio', 'total_amount', 'deposit', 'month_duration', 'first_due_date', 'status', 'sale_date')
    search_fields = ('customer__email', 'customer__physical_detail__first_name', 'commercial__username')
    list_filter = ('status', 'sale_date')
