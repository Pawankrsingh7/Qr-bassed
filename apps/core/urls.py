from django.urls import path

from apps.orders.views import customer_order_page

from .views import cashier_dashboard, cashier_invoice_pdf, home, order_scan_entry, role_home_redirect, waiter_dashboard

app_name = 'core'

urlpatterns = [
    path('', home, name='home'),
    path('home-redirect/', role_home_redirect, name='role-home-redirect'),
    path('staff/', waiter_dashboard, name='staff-dashboard'),
    path('cashier/', cashier_dashboard, name='cashier-dashboard'),
    path('cashier/invoice/<int:session_id>/pdf/', cashier_invoice_pdf, name='cashier-invoice-pdf'),
    path('order/', order_scan_entry, name='order-entry'),
    path(
        'order/<slug:restaurant_slug>/<int:table_number>/<str:qr_token>/',
        customer_order_page,
        name='scan-order',
    ),
]
