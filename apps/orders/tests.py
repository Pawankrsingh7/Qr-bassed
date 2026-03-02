from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.menu.models import MenuCategory, MenuItem
from apps.orders.models import OrderSession
from apps.restaurants.models import Restaurant
from apps.tables.models import Table


class OrderFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.restaurant = Restaurant.objects.create(name='Test Resto', slug='test-resto')
        self.table = Table.objects.create(restaurant=self.restaurant, table_number=1, verification_pin='1234')
        category = MenuCategory.objects.create(restaurant=self.restaurant, name='Main', display_order=1)
        self.menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=category,
            name='Burger',
            description='Test burger',
            price='150.00',
            available=True,
        )
        self.staff = get_user_model().objects.create_user(username='staff1', password='pass12345', is_staff=True)

    def test_full_session_flow_with_staff_confirmation(self):
        bootstrap = self.client.post(
            '/api/customer/sessions/bootstrap/',
            {
                'restaurant_slug': self.restaurant.slug,
                'table_number': self.table.table_number,
                'verification_pin': '1234',
            },
            format='json',
        )
        self.assertEqual(bootstrap.status_code, 200)
        session_id = bootstrap.data['session']['id']

        add_items = self.client.post(
            f'/api/customer/sessions/{session_id}/items/',
            {'items': [{'menu_item_id': self.menu_item.id, 'quantity': 2}]},
            format='json',
        )
        self.assertEqual(add_items.status_code, 201)
        self.assertTrue(add_items.data['requires_staff_confirmation'])

        self.client.force_authenticate(self.staff)
        confirm = self.client.post(f'/api/customer/sessions/{session_id}/confirm/', format='json')
        self.assertEqual(confirm.status_code, 200)
        self.assertEqual(confirm.data['session']['status'], OrderSession.Status.ACTIVE)

        request_bill = self.client.post(f'/api/customer/sessions/{session_id}/request-bill/', format='json')
        self.assertEqual(request_bill.status_code, 200)
        self.assertEqual(request_bill.data['session']['status'], OrderSession.Status.PAYMENT_REQUESTED)

    def test_bootstrap_rejects_wrong_pin(self):
        response = self.client.post(
            '/api/customer/sessions/bootstrap/',
            {
                'restaurant_slug': self.restaurant.slug,
                'table_number': self.table.table_number,
                'verification_pin': '9999',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 403)
