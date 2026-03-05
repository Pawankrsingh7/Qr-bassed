from django.db import models

from apps.orders.models import OrderSession


class SessionBilling(models.Model):
    session = models.OneToOneField(OrderSession, on_delete=models.CASCADE, related_name='billing')
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=40, blank=True)
    coupon_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    split_count = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f'Billing - Session {self.session_id}'


class PaymentTransaction(models.Model):
    class Method(models.TextChoices):
        CASH = 'cash', 'Cash'
        UPI = 'upi', 'UPI'
        CARD = 'card', 'Card'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
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
