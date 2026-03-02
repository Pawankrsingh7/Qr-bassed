from django.urls import path

from apps.orders.views import customer_order_page

from .views import home, order_scan_entry

app_name = 'core'

urlpatterns = [
    path('', home, name='home'),
    path('order/', order_scan_entry, name='order-entry'),
    path(
        'order/<slug:restaurant_slug>/<int:table_number>/<str:qr_token>/',
        customer_order_page,
        name='scan-order',
    ),
]
