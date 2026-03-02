from django.urls import include, path

urlpatterns = [
    path('customer/', include('apps.orders.urls')),
    path('menu/', include('apps.menu.urls')),
    path('tables/', include('apps.tables.urls')),
    path('payments/', include('apps.payments.urls')),
    path('kitchen/', include('apps.kitchen.api_urls')),
    path('dashboard/', include('apps.dashboard.api_urls')),
]
