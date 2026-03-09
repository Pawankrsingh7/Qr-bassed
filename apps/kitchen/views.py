from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.roles import ROLE_KITCHEN, get_role_home_url, get_user_role
from apps.orders.models import OrderItem, OrderSession
from apps.orders.services import release_due_paid_sessions


@login_required
def kitchen_dashboard(request):
    if get_user_role(request.user) != ROLE_KITCHEN:
        return redirect(get_role_home_url(request.user))

    release_due_paid_sessions()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_item_status':
            item = get_object_or_404(OrderItem.objects.select_related('session'), id=request.POST.get('item_id'))
            next_status = request.POST.get('next_status')
            if next_status in {OrderItem.Status.PREPARING, OrderItem.Status.READY, OrderItem.Status.SERVED}:
                item.status = next_status
                item.save(update_fields=['status'])
                messages.success(request, f'Updated item #{item.id} to {item.status}.')
            else:
                messages.error(request, 'Invalid status update request.')
            return redirect('/kitchen/')

    queue_items = (
        OrderItem.objects.select_related('session', 'session__table', 'session__table__restaurant', 'menu_item')
        .filter(
            session__status__in=[OrderSession.Status.ACTIVE, OrderSession.Status.PAYMENT_REQUESTED],
            status__in=[OrderItem.Status.ORDERED, OrderItem.Status.PREPARING],
        )
        .order_by('created_at')
    )
    queue_paginator = Paginator(queue_items, 15)
    queue_page_obj = queue_paginator.get_page(request.GET.get('queue_page'))

    ready_count = (
        OrderItem.objects.filter(
            session__status__in=[OrderSession.Status.ACTIVE, OrderSession.Status.PAYMENT_REQUESTED],
            status=OrderItem.Status.READY,
        )
        .count()
    )

    prepared_items = (
        OrderItem.objects.select_related('session', 'session__table', 'session__table__restaurant', 'menu_item')
        .filter(status__in=[OrderItem.Status.READY, OrderItem.Status.SERVED])
        .order_by('-created_at')[:250]
    )
    prepared_paginator = Paginator(prepared_items, 15)
    prepared_page_obj = prepared_paginator.get_page(request.GET.get('history_page'))

    return render(
        request,
        'kitchen/dashboard.html',
        {
            'queue_items': queue_page_obj,
            'prepared_items': prepared_page_obj,
            'ready_count': ready_count,
        },
    )
