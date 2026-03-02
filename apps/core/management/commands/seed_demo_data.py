from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.menu.models import MenuCategory, MenuItem
from apps.restaurants.models import Restaurant
from apps.tables.models import Table


class Command(BaseCommand):
    help = 'Seed demo data for Smart Restaurant Ordering System.'

    def handle(self, *args, **options):
        restaurant, _ = Restaurant.objects.get_or_create(
            slug='demo-restaurant',
            defaults={'name': 'Demo Restaurant', 'is_active': True},
        )

        for table_number in range(1, 11):
            Table.objects.get_or_create(restaurant=restaurant, table_number=table_number)

        starters, _ = MenuCategory.objects.get_or_create(restaurant=restaurant, name='Starters', defaults={'display_order': 1})
        mains, _ = MenuCategory.objects.get_or_create(restaurant=restaurant, name='Main Course', defaults={'display_order': 2})
        drinks, _ = MenuCategory.objects.get_or_create(restaurant=restaurant, name='Drinks', defaults={'display_order': 3})

        items = [
            (starters, 'Paneer Tikka', 'Tandoor grilled cottage cheese', '249.00'),
            (starters, 'Veg Spring Roll', 'Crispy rolls with dipping sauce', '179.00'),
            (mains, 'Butter Chicken', 'Creamy tomato gravy', '349.00'),
            (mains, 'Veg Biryani', 'Aromatic basmati rice', '299.00'),
            (drinks, 'Fresh Lime Soda', 'Sweet or salted', '99.00'),
            (drinks, 'Cold Coffee', 'Chilled coffee with ice cream', '149.00'),
        ]

        for category, name, description, price in items:
            MenuItem.objects.get_or_create(
                restaurant=restaurant,
                category=category,
                name=name,
                defaults={'description': description, 'price': price, 'available': True},
            )

        User = get_user_model()
        if not User.objects.filter(username='staff').exists():
            User.objects.create_user(username='staff', password='staff1234', is_staff=True)

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
        self.stdout.write('Staff login: username=staff password=staff1234')
