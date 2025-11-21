from django.contrib import admin
from .models import Debt, Term, Recovery

@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ('id','sale','init_amount','balance','start_date','status')
    search_fields = ('sale__customer__email',)

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('id','debt','term_date','except_amount','pay_amount','status')
    list_filter = ('status',)

@admin.register(Recovery)
class RecoveryAdmin(admin.ModelAdmin):
    list_display = ('id','term','commercial','amount','date','payment_mode')
    search_fields = ('commercial__username',)
