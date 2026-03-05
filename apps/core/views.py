from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import ExtractHour
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.menu.models import MenuItem
from apps.orders.models import OrderItem, OrderSession
from apps.orders.services import confirm_session, reject_session, release_due_paid_sessions
from apps.payments.models import PaymentTransaction
from apps.payments.services import (
    add_item_to_bill,
    calculate_bill_summary,
    mark_payment,
    remove_item_from_bill,
    update_billing_config,
)
from apps.tables.models import Table

from .roles import ROLE_CASHIER, ROLE_WAITER, get_role_home_url, get_user_role


def home(request):
    return render(request, 'core/home.html')


@login_required
def role_home_redirect(request):
    return redirect(get_role_home_url(request.user))


@login_required
def waiter_dashboard(request):
    if get_user_role(request.user) != ROLE_WAITER:
        return redirect(get_role_home_url(request.user))

    release_due_paid_sessions()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve_session':
            session_id = request.POST.get('session_id')
            session = get_object_or_404(OrderSession, id=session_id)
            confirm_session(session=session, user=request.user)
            messages.success(request, f'Session #{session.id} approved successfully.')
            return redirect('/staff/')
        if action == 'reject_session':
            session_id = request.POST.get('session_id')
            session = get_object_or_404(OrderSession, id=session_id)
            reject_session(session=session)
            messages.success(request, f'Session #{session.id} rejected and terminated.')
            return redirect('/staff/')
        if action == 'mark_served':
            item = get_object_or_404(OrderItem, id=request.POST.get('item_id'))
            if item.status == OrderItem.Status.READY:
                item.status = OrderItem.Status.SERVED
                item.save(update_fields=['status'])
                messages.success(request, f'Item "{item.menu_item.name}" marked as served.')
            else:
                messages.error(request, 'Only ready items can be served.')
            return redirect('/staff/')

    pending_sessions = (
        OrderSession.objects.select_related('table', 'table__restaurant')
        .filter(status=OrderSession.Status.PENDING_CONFIRMATION)
        .annotate(item_count=Count('items'))
        .filter(item_count__gt=0)
        .order_by('created_at')
    )
    ready_items = (
        OrderItem.objects.select_related('session', 'session__table', 'session__table__restaurant', 'menu_item')
        .filter(status=OrderItem.Status.READY, session__status__in=[OrderSession.Status.ACTIVE, OrderSession.Status.PAYMENT_REQUESTED])
        .order_by('created_at')
    )
    return render(
        request,
        'staff/dashboard.html',
        {
            'pending_sessions': pending_sessions,
            'ready_items': ready_items,
        },
    )


@login_required
def cashier_dashboard(request):
    if get_user_role(request.user) != ROLE_CASHIER:
        return redirect(get_role_home_url(request.user))

    release_due_paid_sessions()

    section = request.GET.get('section', 'billing')
    valid_sections = {'billing', 'table_status', 'daily_sales', 'order_history'}
    if section not in valid_sections:
        section = 'billing'

    active_bill_sessions = (
        OrderSession.objects.select_related('table', 'table__restaurant')
        .filter(status__in=[OrderSession.Status.PAYMENT_REQUESTED, OrderSession.Status.PAID])
        .order_by('-created_at')
    )
    selected_session = None

    requested_session_id = request.GET.get('session_id') or request.POST.get('session_id')
    if requested_session_id:
        selected_session = active_bill_sessions.filter(id=requested_session_id).first()
    if not selected_session:
        selected_session = active_bill_sessions.first()

    if request.method == 'POST':
        action = request.POST.get('action')
        session = get_object_or_404(OrderSession, id=request.POST.get('session_id')) if request.POST.get('session_id') else selected_session

        if action == 'update_billing' and session:
            gst_percent = Decimal(request.POST.get('gst_percent') or '5')
            discount_amount = Decimal(request.POST.get('discount_amount') or '0')
            coupon_code = request.POST.get('coupon_code', '')
            split_count = int(request.POST.get('split_count') or 1)
            update_billing_config(session, gst_percent, discount_amount, coupon_code, split_count)
            messages.success(request, 'Billing rules updated.')
            return redirect(f'/cashier/?section=billing&session_id={session.id}')

        if action == 'add_item' and session:
            menu_item = get_object_or_404(MenuItem, id=request.POST.get('menu_item_id'), available=True)
            quantity = int(request.POST.get('quantity') or 1)
            add_item_to_bill(session, menu_item, max(1, quantity))
            messages.success(request, 'Item added to bill.')
            return redirect(f'/cashier/?section=billing&session_id={session.id}')

        if action == 'remove_item' and session:
            remove_item_from_bill(session, int(request.POST.get('order_item_id')))
            messages.success(request, 'Item removed from bill.')
            return redirect(f'/cashier/?section=billing&session_id={session.id}')

        if action == 'mark_payment_done' and session:
            summary = calculate_bill_summary(session)
            method = request.POST.get('payment_method', PaymentTransaction.Method.CASH)
            if method not in {PaymentTransaction.Method.CASH, PaymentTransaction.Method.UPI, PaymentTransaction.Method.CARD}:
                method = PaymentTransaction.Method.CASH
            mark_payment(session=session, amount=summary['final_total'], method=method)
            messages.success(
                request,
                f'Session #{session.id} paid ({method}). Table auto-free in {session.release_after_minutes} minutes.',
            )
            return redirect('/cashier/?section=billing')

    bill_summary = calculate_bill_summary(selected_session) if selected_session else None
    bill_items = selected_session.items.select_related('menu_item').all() if selected_session else []

    all_available_menu_items = MenuItem.objects.filter(available=True).select_related('restaurant', 'category').order_by('restaurant__name', 'name')

    table_qs = Table.objects.select_related('restaurant').order_by('restaurant__name', 'table_number')
    table_orders = (
        OrderSession.objects.select_related('table', 'table__restaurant')
        .filter(status__in=[OrderSession.Status.ACTIVE, OrderSession.Status.PAYMENT_REQUESTED, OrderSession.Status.PAID])
        .order_by('-created_at')[:100]
    )
    table_status = {
        'available': table_qs.filter(status=Table.Status.FREE).count(),
        'occupied': table_qs.filter(status__in=[Table.Status.ACTIVE, Table.Status.PAID]).count(),
        'reserved': table_qs.filter(status=Table.Status.RESERVED).count(),
    }

    today = timezone.localdate()
    today_payments = PaymentTransaction.objects.filter(status=PaymentTransaction.Status.PAID, created_at__date=today)
    total_sales_today = today_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_orders_today = OrderSession.objects.filter(created_at__date=today).count()
    cash_sales = today_payments.filter(method=PaymentTransaction.Method.CASH).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    online_sales = today_payments.filter(method__in=[PaymentTransaction.Method.UPI, PaymentTransaction.Method.CARD]).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    most_sold_items = (
        OrderItem.objects.filter(session__created_at__date=today)
        .values('menu_item__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )
    peak_order = (
        OrderSession.objects.filter(created_at__date=today)
        .annotate(hour=ExtractHour('created_at'))
        .values('hour')
        .annotate(cnt=Count('id'))
        .order_by('-cnt', 'hour')
        .first()
    )

    history_qs = OrderSession.objects.select_related('table', 'table__restaurant').order_by('-created_at')
    filter_date = request.GET.get('filter_date')
    filter_order_id = request.GET.get('filter_order_id')
    filter_table = request.GET.get('filter_table')

    if filter_date:
        history_qs = history_qs.filter(created_at__date=filter_date)
    if filter_order_id:
        history_qs = history_qs.filter(id=filter_order_id)
    if filter_table:
        history_qs = history_qs.filter(table__table_number=filter_table)
    history_qs = history_qs[:200]

    context = {
        'section': section,
        'active_bill_sessions': active_bill_sessions,
        'selected_session': selected_session,
        'bill_summary': bill_summary,
        'bill_items': bill_items,
        'all_available_menu_items': all_available_menu_items,
        'table_status': table_status,
        'table_orders': table_orders,
        'total_sales_today': total_sales_today,
        'total_orders_today': total_orders_today,
        'cash_sales': cash_sales,
        'online_sales': online_sales,
        'most_sold_items': most_sold_items,
        'peak_order': peak_order,
        'history_qs': history_qs,
        'filter_date': filter_date or '',
        'filter_order_id': filter_order_id or '',
        'filter_table': filter_table or '',
    }
    return render(request, 'cashier/dashboard.html', context)


@login_required
def cashier_invoice_pdf(request, session_id: int):
    if get_user_role(request.user) != ROLE_CASHIER:
        return redirect(get_role_home_url(request.user))

    session = get_object_or_404(OrderSession.objects.select_related('table', 'table__restaurant'), id=session_id)
    summary = calculate_bill_summary(session)
    items = session.items.select_related('menu_item').all()

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception:
        return HttpResponse('PDF library unavailable. Install reportlab.', status=500)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_session_{session.id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    y = 800
    p.drawString(40, y, f'Invoice - Session #{session.id}')
    y -= 20
    p.drawString(40, y, f'Restaurant: {session.table.restaurant.name}')
    y -= 20
    p.drawString(40, y, f'Table: {session.table.table_number}')
    y -= 20
    p.drawString(40, y, f'Customer: {session.customer_name or "Guest"}')
    y -= 30

    p.drawString(40, y, 'Items:')
    y -= 20
    for item in items:
        line = f'- {item.menu_item.name} x {item.quantity} @ {item.price}'
        p.drawString(50, y, line[:100])
        y -= 18
        if y < 80:
            p.showPage()
            y = 800

    y -= 10
    p.drawString(40, y, f'Subtotal: {summary["subtotal"]}')
    y -= 20
    p.drawString(40, y, f'GST: {summary["gst_amount"]}')
    y -= 20
    p.drawString(40, y, f'Discount: {summary["discount_amount"] + summary["coupon_discount_amount"]}')
    y -= 20
    p.drawString(40, y, f'Final Total: {summary["final_total"]}')
    y -= 20
    p.drawString(40, y, f'Split ({summary["split_count"]}): {summary["per_person"]} each')

    p.showPage()
    p.save()
    return response


def order_scan_entry(request):
    return redirect('/')
