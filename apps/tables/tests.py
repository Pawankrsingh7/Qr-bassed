from django.test import TestCase

from apps.restaurants.models import Restaurant
from apps.tables.models import Table


class TableQRViewsTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='QR Resto', slug='qr-resto')
        self.table = Table.objects.create(restaurant=self.restaurant, table_number=5)

    def test_qr_svg_endpoint_returns_svg(self):
        response = self.client.get(
            f'/tables/restaurants/{self.restaurant.slug}/tables/{self.table.table_number}/{self.table.qr_token}/qr.svg'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')

    def test_qr_catalog_page_loads(self):
        response = self.client.get(f'/tables/restaurants/{self.restaurant.slug}/qr-catalog/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Table {self.table.table_number}')
