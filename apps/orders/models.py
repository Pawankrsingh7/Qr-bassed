from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.utils import timezone

from apps.menu.models import MenuItem
from apps.tables.models import Table


class OrderSession(models.Model):
    class Status(models.TextChoices):
        PENDING_CONFIRMATION = 'pending_confirmation', 'Pending Confirmation'
        ACTIVE = 'active', 'Active'
        PAYMENT_REQUESTED = 'payment_requested', 'Payment Requested'
        PAID = 'paid', 'Paid'
        CLOSED = 'closed', 'Closed'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'

    table = models.ForeignKey(Table, on_delete=models.PROTECT, related_name='sessions')
    customer_name = models.CharField(max_length=120, blank=True, default='')
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING_CONFIRMATION)
    payment_status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    confirmed_by = models.ForeignKey(
        'auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='confirmed_sessions'
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    release_after_minutes = models.PositiveSmallIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Session {self.id} - Table {self.table.table_number}'

    @property
    def is_open(self) -> bool:
        return self.status in {
            self.Status.PENDING_CONFIRMATION,
            self.Status.ACTIVE,
            self.Status.PAYMENT_REQUESTED,
        }

    def mark_active(self, user=None):
        self.status = self.Status.ACTIVE
        self.table.status = Table.Status.ACTIVE
        self.confirmed_by = user
        self.confirmed_at = timezone.now()
        self.table.save(update_fields=['status'])
        self.save(update_fields=['status', 'confirmed_by', 'confirmed_at'])

    def close_as_paid(self, release_after_minutes: int = 5):
        self.payment_status = self.PaymentStatus.PAID
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.release_after_minutes = release_after_minutes
        self.table.status = Table.Status.PAID
        self.table.save(update_fields=['status'])
        self.save(update_fields=['payment_status', 'status', 'paid_at', 'release_after_minutes'])

    def release_if_due(self) -> bool:
        if self.status != self.Status.PAID or not self.paid_at:
            return False
        if timezone.now() < self.paid_at + timezone.timedelta(minutes=self.release_after_minutes):
            return False
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.table.status = Table.Status.FREE
        self.table.save(update_fields=['status'])
        self.save(update_fields=['status', 'closed_at'])
        return True

    def recalculate_total(self):
        total = self.items.aggregate(total=Sum(models.F('price') * models.F('quantity')))['total']
        self.total_amount = total or Decimal('0.00')
        self.save(update_fields=['total_amount'])
        return self.total_amount


class OrderItem(models.Model):
    class Status(models.TextChoices):
        ORDERED = 'ordered', 'Ordered'
        PREPARING = 'preparing', 'Preparing'
        READY = 'ready', 'Ready'
        SERVED = 'served', 'Served'

    session = models.ForeignKey(OrderSession, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ORDERED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'{self.menu_item.name} x {self.quantity}'
