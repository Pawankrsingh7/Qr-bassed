from django.db import models

from apps.restaurants.models import Restaurant
from apps.tables.utils import generate_qr_token, generate_table_pin


class Table(models.Model):
    class Status(models.TextChoices):
        FREE = 'free', 'Free'
        ACTIVE = 'active', 'Active'
        PAID = 'paid', 'Paid'

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_number = models.PositiveIntegerField()
    qr_token = models.CharField(max_length=64, unique=True, default=generate_qr_token, editable=False)
    verification_pin = models.CharField(max_length=4, default=generate_table_pin)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.FREE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['restaurant_id', 'table_number']
        constraints = [
            models.UniqueConstraint(fields=['restaurant', 'table_number'], name='uniq_restaurant_table_number')
        ]

    def __str__(self) -> str:
        return f'{self.restaurant.name} - Table {self.table_number}'

    @property
    def qr_path(self) -> str:
        return f'/order/{self.restaurant.slug}/{self.table_number}/{self.qr_token}/'
