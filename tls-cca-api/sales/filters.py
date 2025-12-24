from core.filters import BaseDateRangeFilter
from .models import CreditSale

class CreditSaleFilter(BaseDateRangeFilter):
    class Meta:
        model = CreditSale
        fields = ['commercial', 'customer', 'status', 'portfolio']
        date_field = 'sale_date'