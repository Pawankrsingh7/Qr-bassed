from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
            status__in=[OrderItem.Status.ORDERED, OrderItem.Status.PREPARING, OrderItem.Status.READY],
        )
        .order_by('created_at')
    )

    return render(request, 'kitchen/dashboard.html', {'queue_items': queue_items})
