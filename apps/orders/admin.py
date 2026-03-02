from django.contrib import admin

from .models import OrderItem, OrderSession


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('menu_item', 'quantity', 'price', 'status', 'created_at')


@admin.register(OrderSession)
class OrderSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'table', 'status', 'payment_status', 'total_amount', 'created_at')
    list_filter = ('status', 'payment_status', 'table__restaurant')
    search_fields = ('table__table_number',)
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'menu_item', 'quantity', 'price', 'status', 'created_at')
    list_filter = ('status', 'menu_item__restaurant')
    search_fields = ('menu_item__name', 'session__table__table_number')
