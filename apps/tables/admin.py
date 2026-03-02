from django.contrib import admin

from .models import Table


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('id', 'restaurant', 'table_number', 'status', 'verification_pin', 'is_active')
    list_filter = ('restaurant', 'status', 'is_active')
    search_fields = ('restaurant__name', 'table_number', 'qr_token')
    readonly_fields = ('qr_token',)
