from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.menu.models import MenuCategory, MenuItem
from apps.orders.models import OrderItem, OrderSession
from apps.payments.models import PaymentTransaction
from apps.restaurants.models import Restaurant
from apps.tables.models import Table


class CashPaymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.restaurant = Restaurant.objects.create(name='Pay Resto', slug='pay-resto')
        self.table = Table.objects.create(restaurant=self.restaurant, table_number=3)
        category = MenuCategory.objects.create(restaurant=self.restaurant, name='Main', display_order=1)
        menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=category,
            name='Pasta',
            description='White sauce',
            price='220.00',
            available=True,
        )
        self.session = OrderSession.objects.create(table=self.table, status=OrderSession.Status.PAYMENT_REQUESTED)
        OrderItem.objects.create(session=self.session, menu_item=menu_item, quantity=2, price='220.00')
        self.session.recalculate_total()
        self.staff = get_user_model().objects.create_user(username='paystaff', password='pass12345', is_staff=True)

    def test_cash_payment_closes_session(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            f'/api/payments/sessions/{self.session.id}/cash/',
            {'amount': '440.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.table.refresh_from_db()
        self.assertEqual(self.session.status, OrderSession.Status.CLOSED)
        self.assertEqual(self.session.payment_status, OrderSession.PaymentStatus.PAID)
        self.assertEqual(self.table.status, Table.Status.FREE)
        self.assertTrue(PaymentTransaction.objects.filter(session=self.session).exists())
