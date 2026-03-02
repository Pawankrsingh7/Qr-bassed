from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.menu.models import MenuCategory, MenuItem
from apps.orders.models import OrderItem, OrderSession
from apps.restaurants.models import Restaurant
from apps.tables.models import Table


class KitchenPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.restaurant = Restaurant.objects.create(name='Test Kitchen', slug='test-kitchen')
        self.table = Table.objects.create(restaurant=self.restaurant, table_number=2)
        category = MenuCategory.objects.create(restaurant=self.restaurant, name='Main', display_order=1)
        menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=category,
            name='Pizza',
            description='Cheese',
            price='200.00',
            available=True,
        )
        self.session = OrderSession.objects.create(table=self.table, status=OrderSession.Status.ACTIVE)
        self.item = OrderItem.objects.create(session=self.session, menu_item=menu_item, quantity=1, price='200.00')
        self.staff = get_user_model().objects.create_user(username='kstaff', password='pass12345', is_staff=True)

    def test_kitchen_queue_requires_staff(self):
        response = self.client.get('/api/kitchen/queue/')
        self.assertEqual(response.status_code, 403)

    def test_kitchen_status_update_for_staff(self):
        self.client.force_authenticate(self.staff)
        response = self.client.patch(
            f'/api/kitchen/order-items/{self.item.id}/status/',
            {'status': OrderItem.Status.PREPARING},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, OrderItem.Status.PREPARING)

    def test_pending_confirmation_order_visible_in_kitchen_queue(self):
        self.session.status = OrderSession.Status.PENDING_CONFIRMATION
        self.session.save(update_fields=['status'])

        self.client.force_authenticate(self.staff)
        response = self.client.get('/api/kitchen/queue/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['orders']), 1)
        self.assertEqual(response.data['orders'][0]['session_status'], OrderSession.Status.PENDING_CONFIRMATION)
