from django.core.management.base import BaseCommand

from apps.tables.models import Table
from apps.tables.utils import generate_table_pin


class Command(BaseCommand):
    help = 'Rotate table verification PINs.'

    def add_arguments(self, parser):
        parser.add_argument('--restaurant-slug', type=str, required=False)

    def handle(self, *args, **options):
        queryset = Table.objects.all()
        if options.get('restaurant_slug'):
            queryset = queryset.filter(restaurant__slug=options['restaurant_slug'])

        count = 0
        for table in queryset:
            table.verification_pin = generate_table_pin()
            table.save(update_fields=['verification_pin'])
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Rotated PINs for {count} tables.'))
