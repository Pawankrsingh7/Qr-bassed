from django.contrib import admin

from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'method', 'amount', 'status', 'created_at')
    list_filter = ('method', 'status')
    search_fields = ('session__id', 'external_reference')
