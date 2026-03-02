from django.urls import path

from .views import table_qr_catalog_page, table_qr_svg

app_name = 'tables_web'

urlpatterns = [
    path('restaurants/<slug:restaurant_slug>/qr-catalog/', table_qr_catalog_page, name='qr-catalog'),
    path(
        'restaurants/<slug:restaurant_slug>/tables/<int:table_number>/<str:qr_token>/qr.svg',
        table_qr_svg,
        name='table-qr-svg',
    ),
]
