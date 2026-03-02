from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.restaurants.models import Restaurant
from apps.tables.models import Table


class DashboardAdminTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='Dash Resto', slug='dash-resto')
        self.staff = get_user_model().objects.create_user(username='admin1', password='pass12345', is_staff=True)

    def test_dashboard_requires_login(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_staff_can_generate_tables(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            '/dashboard/',
            {
                'action': 'generate_tables',
                'restaurant': self.restaurant.id,
                'table_count': 4,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Table.objects.filter(restaurant=self.restaurant).count(), 4)

    def test_generate_tables_keeps_existing_and_fills_missing(self):
        Table.objects.create(restaurant=self.restaurant, table_number=1)
        self.client.force_login(self.staff)
        self.client.post(
            '/dashboard/',
            {
                'action': 'generate_tables',
                'restaurant': self.restaurant.id,
                'table_count': 3,
            },
        )
        numbers = list(Table.objects.filter(restaurant=self.restaurant).order_by('table_number').values_list('table_number', flat=True))
        self.assertEqual(numbers, [1, 2, 3])
