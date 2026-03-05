from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.menu.models import MenuItem
from apps.tables.models import Table

from .models import OrderItem, OrderSession


def get_or_create_open_session(table: Table, force_new_session: bool = False, customer_name: str = '') -> OrderSession:
    open_statuses = [
        OrderSession.Status.PENDING_CONFIRMATION,
        OrderSession.Status.ACTIVE,
        OrderSession.Status.PAYMENT_REQUESTED,
    ]
    session = table.sessions.filter(status__in=open_statuses).order_by('-created_at').first()
    if session and auto_cancel_stale_pending(session):
        session = None

    if session and not force_new_session:
        if customer_name and not session.customer_name:
            session.customer_name = customer_name
            session.save(update_fields=['customer_name'])
        return session

    if session and force_new_session:
        session.status = OrderSession.Status.CANCELLED
        session.save(update_fields=['status'])

    table.status = Table.Status.ACTIVE
    table.save(update_fields=['status'])
    return OrderSession.objects.create(
        table=table,
        status=OrderSession.Status.PENDING_CONFIRMATION,
        customer_name=customer_name or '',
    )


@transaction.atomic
def add_items_to_session(session: OrderSession, payload_items):
    if session.status in (OrderSession.Status.CLOSED, OrderSession.Status.CANCELLED):
        raise serializers.ValidationError('This session is closed. Please start a new session.')

    menu_item_map = {
        item.id: item
        for item in MenuItem.objects.filter(
            id__in=[item['menu_item_id'] for item in payload_items],
            restaurant=session.table.restaurant,
            available=True,
        )
    }

    created_items = []
    for payload in payload_items:
        menu_item = menu_item_map.get(payload['menu_item_id'])
        if not menu_item:
            raise serializers.ValidationError(f"Menu item {payload['menu_item_id']} is unavailable.")

        created_items.append(
            OrderItem.objects.create(
                session=session,
                menu_item=menu_item,
                quantity=payload['quantity'],
                price=menu_item.price,
                status=OrderItem.Status.ORDERED,
            )
        )

    session.recalculate_total()
    return created_items


@transaction.atomic
def confirm_session(session: OrderSession, user=None) -> OrderSession:
    if session.status != OrderSession.Status.PENDING_CONFIRMATION:
        return session

    session.mark_active(user=user)
    return session


@transaction.atomic
def reject_session(session: OrderSession) -> OrderSession:
    if session.status in (OrderSession.Status.CLOSED, OrderSession.Status.CANCELLED):
        return session

    session.status = OrderSession.Status.CANCELLED
    session.closed_at = timezone.now()
    session.table.status = Table.Status.FREE
    session.table.save(update_fields=['status'])
    session.save(update_fields=['status', 'closed_at'])
    return session


@transaction.atomic
def request_bill(session: OrderSession) -> OrderSession:
    if session.status in (OrderSession.Status.CLOSED, OrderSession.Status.CANCELLED):
        return session

    session.status = OrderSession.Status.PAYMENT_REQUESTED
    session.save(update_fields=['status'])
    return session


@transaction.atomic
def auto_cancel_stale_pending(session: OrderSession, timeout_minutes: int = 10) -> bool:
    if session.status != OrderSession.Status.PENDING_CONFIRMATION:
        return False

    if timezone.now() - session.created_at < timedelta(minutes=timeout_minutes):
        return False

    session.status = OrderSession.Status.CANCELLED
    session.table.status = Table.Status.FREE
    session.table.save(update_fields=['status'])
    session.save(update_fields=['status'])
    return True


@transaction.atomic
def release_due_paid_sessions() -> int:
    paid_sessions = OrderSession.objects.select_related('table').filter(status=OrderSession.Status.PAID)
    released_count = 0
    for session in paid_sessions:
        if session.release_if_due():
            released_count += 1
    return released_count
