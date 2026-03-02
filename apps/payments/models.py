from django.db import models

from apps.orders.models import OrderSession


class PaymentTransaction(models.Model):
    class Method(models.TextChoices):
        CASH = 'cash', 'Cash'
        ONLINE = 'online', 'Online'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    session = models.ForeignKey(OrderSession, on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=16, choices=Method.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    external_reference = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Payment {self.id} - Session {self.session_id}'
