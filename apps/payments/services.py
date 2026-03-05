from decimal import Decimal
from django.db import transaction
import random

from apps.orders.models import OrderItem, OrderSession

from .models import PaymentTransaction, SessionBilling


def get_or_create_session_billing(session: OrderSession) -> SessionBilling:
    billing, _ = SessionBilling.objects.get_or_create(session=session)
    return billing


def calculate_bill_summary(session: OrderSession):
    billing = get_or_create_session_billing(session)
    subtotal = session.total_amount or Decimal('0.00')
    gst_amount = (subtotal * billing.gst_percent / Decimal('100')).quantize(Decimal('0.01'))
    total_discount = (billing.discount_amount + billing.coupon_discount_amount).quantize(Decimal('0.01'))
    gross_total = (subtotal + gst_amount - total_discount).quantize(Decimal('0.01'))
    final_total = gross_total if gross_total > Decimal('0.00') else Decimal('0.00')
    split_count = billing.split_count if billing.split_count > 0 else 1
    per_person = (final_total / Decimal(split_count)).quantize(Decimal('0.01'))

    return {
        'billing': billing,
        'subtotal': subtotal,
        'gst_amount': gst_amount,
        'discount_amount': billing.discount_amount,
        'coupon_code': billing.coupon_code,
        'coupon_discount_amount': billing.coupon_discount_amount,
        'final_total': final_total,
        'split_count': split_count,
        'per_person': per_person,
    }


@transaction.atomic
def update_billing_config(
    session: OrderSession,
    gst_percent: Decimal,
    discount_amount: Decimal,
    coupon_code: str,
    split_count: int,
):
    billing = get_or_create_session_billing(session)

    coupon_map = {
        'SAVE10': Decimal('10.00'),
        'FLAT50': Decimal('50.00'),
        'WELCOME': Decimal('25.00'),
    }

    billing.gst_percent = gst_percent
    billing.discount_amount = discount_amount
    billing.coupon_code = coupon_code.strip().upper()
    billing.coupon_discount_amount = coupon_map.get(billing.coupon_code, Decimal('0.00'))
    billing.split_count = split_count if split_count > 0 else 1
    billing.save()
    return billing


@transaction.atomic
def add_item_to_bill(session: OrderSession, menu_item, quantity: int):
    item = OrderItem.objects.filter(session=session, menu_item=menu_item, status=OrderItem.Status.ORDERED).first()
    if item:
        item.quantity += quantity
        item.save(update_fields=['quantity'])
    else:
        item = OrderItem.objects.create(
            session=session,
            menu_item=menu_item,
            quantity=quantity,
            price=menu_item.price,
            status=OrderItem.Status.ORDERED,
        )
    session.recalculate_total()
    return item


@transaction.atomic
def remove_item_from_bill(session: OrderSession, order_item_id: int):
    item = OrderItem.objects.filter(id=order_item_id, session=session).first()
    if not item:
        return False
    item.delete()
    session.recalculate_total()
    return True


@transaction.atomic
def mark_payment(session: OrderSession, amount, method: str):
    if session.payment_status == OrderSession.PaymentStatus.PAID:
        return session.payments.filter(status=PaymentTransaction.Status.PAID).order_by('-created_at').first()

    payment = PaymentTransaction.objects.create(
        session=session,
        method=method,
        amount=amount,
        status=PaymentTransaction.Status.PAID,
    )
    session.close_as_paid(release_after_minutes=random.randint(5, 7))
    return payment


@transaction.atomic
def mark_cash_payment(session: OrderSession, amount):
    return mark_payment(session=session, amount=amount, method=PaymentTransaction.Method.CASH)


@transaction.atomic
def mark_online_payment(session: OrderSession, amount, external_reference: str = ''):
    payment = mark_payment(session=session, amount=amount, method=PaymentTransaction.Method.UPI)
    if external_reference and payment:
        payment.external_reference = external_reference
        payment.save(update_fields=['external_reference'])
    return payment
