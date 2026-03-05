import io

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.restaurants.models import Restaurant

from .models import Table


class TableListAPIView(APIView):
    def get(self, request, restaurant_slug: str):
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, is_active=True)
        tables = Table.objects.filter(restaurant=restaurant).order_by('table_number')
        data = [
            {
                'id': table.id,
                'table_number': table.table_number,
                'status': table.status,
                'is_active': table.is_active,
                'qr_path': reverse(
                    'core:scan-order',
                    kwargs={
                        'restaurant_slug': restaurant.slug,
                        'table_number': table.table_number,
                        'qr_token': table.qr_token,
                    },
                ),
            }
            for table in tables
        ]
        return Response({'restaurant': restaurant.name, 'tables': data})


def table_qr_catalog_page(request, restaurant_slug: str):
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, is_active=True)
    tables = Table.objects.filter(restaurant=restaurant, is_active=True).order_by('table_number')
    return render(request, 'tables/qr_catalog.html', {'restaurant': restaurant, 'tables': tables})


def table_qr_svg(request, restaurant_slug: str, table_number: int, qr_token: str):
    table = get_object_or_404(
        Table,
        restaurant__slug=restaurant_slug,
        table_number=table_number,
        qr_token=qr_token,
        is_active=True,
        qr_enabled=True,
    )

    import qrcode
    import qrcode.image.svg

    scan_url = request.build_absolute_uri(
        reverse(
            'core:scan-order',
            kwargs={
                'restaurant_slug': table.restaurant.slug,
                'table_number': table.table_number,
                'qr_token': table.qr_token,
            },
        )
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(scan_url)
    qr.make(fit=True)
    image = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)

    stream = io.BytesIO()
    image.save(stream)
    return HttpResponse(stream.getvalue(), content_type='image/svg+xml')
