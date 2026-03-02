from django.db import transaction

from apps.orders.models import OrderSession

from .models import PaymentTransaction


@transaction.atomic
def mark_cash_payment(session: OrderSession, amount):
    payment = PaymentTransaction.objects.create(
        session=session,
        method=PaymentTransaction.Method.CASH,
        amount=amount,
        status=PaymentTransaction.Status.SUCCESS,
    )
    session.close_as_paid()
    return payment
