from core.filters import BaseDateRangeFilter
from .models import Debt, Term, Recovery

class DebtFilter(BaseDateRangeFilter):
    class Meta:
        model = Debt
        fields = ['debt_status', 'sale__customer', 'sale__commercial']
        date_field = 'start_date'

class TermFilter(BaseDateRangeFilter):
    class Meta:
        model = Term
        fields = ['term_status', 'debt__sale__customer', 'debt__sale__commercial']
        date_field = 'term_date'

class RecoveryFilter(BaseDateRangeFilter):
    class Meta:
        model = Recovery
        fields = ['payment_mode', 'commercial']
        date_field = 'date'