from datetime import timedelta
from decimal import Decimal
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, User
from django.db.models import Count, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.core.roles import ROLE_ADMIN, ROLE_CASHIER, get_role_home_url, get_user_role
from apps.menu.models import MenuCategory, MenuItem
from apps.orders.models import OrderItem, OrderSession
from apps.orders.services import release_due_paid_sessions
from apps.payments.models import PaymentTransaction
from apps.restaurants.models import Restaurant
from apps.tables.models import Table
from apps.tables.utils import generate_qr_token, generate_table_pin

from .forms import MenuCategoryForm, MenuItemForm, StaffUserCreateForm, TableGenerateForm


ADMIN_SECTIONS = {
    'overview',
    'menus',
    'categories',
    'tables',
    'staff',
    'orders',
    'payments',
    'reports',
    'qr',
}


def _is_admin_user(user):
    return get_user_role(user) == ROLE_ADMIN


def _is_admin_or_cashier_user(user):
    return get_user_role(user) in {ROLE_ADMIN, ROLE_CASHIER}


def _report_window(report_type: str):
    today = timezone.localdate()
    if report_type == 'weekly':
        return today - timedelta(days=6), today
    if report_type == 'monthly':
        return today - timedelta(days=29), today
    return today, today


@login_required
@user_passes_test(_is_admin_user)
def admin_dashboard(request):
    if get_user_role(request.user) != ROLE_ADMIN:
        return redirect(get_role_home_url(request.user))

    release_due_paid_sessions()

    section = request.GET.get('section', 'overview')
    if section not in ADMIN_SECTIONS:
        section = 'overview'

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_staff':
            staff_form = StaffUserCreateForm(request.POST)
            if staff_form.is_valid():
                user, temp_password = staff_form.save()
                request.session['new_user_credentials'] = {
                    'username': user.username,
                    'password': temp_password,
                    'role': staff_form.cleaned_data['role'],
                }
                messages.success(request, 'Staff account created successfully.')
            else:
                messages.error(request, 'Invalid staff data.')
            return redirect(f"{reverse('dashboard:overview')}?section=staff")

        if action == 'delete_staff':
            user = get_object_or_404(User, id=request.POST.get('user_id'), is_staff=True)
            if user.id == request.user.id:
                messages.error(request, 'You cannot delete your own account.')
            else:
                user.delete()
                messages.success(request, 'Staff account deleted.')
            return redirect(f"{reverse('dashboard:overview')}?section=staff")

        if action == 'update_staff_role':
            user = get_object_or_404(User, id=request.POST.get('user_id'), is_staff=True)
            role = request.POST.get('role', '')
            valid_roles = {'cashier', 'manager', 'kitchen', 'waiter', 'admin'}
            if role not in valid_roles:
                messages.error(request, 'Invalid role selected.')
            else:
                user.groups.clear()
                group, _ = Group.objects.get_or_create(name=role)
                user.groups.add(group)
                messages.success(request, 'Staff role updated.')
            return redirect(f"{reverse('dashboard:overview')}?section=staff")

        if action == 'reset_staff_password':
            user = get_object_or_404(User, id=request.POST.get('user_id'), is_staff=True)
            new_password = request.POST.get('new_password', '').strip()
            if len(new_password) < 6:
                messages.error(request, 'Password must be at least 6 characters.')
            else:
                user.set_password(new_password)
                user.save(update_fields=['password'])
                messages.success(request, f'Password reset for {user.username}.')
            return redirect(f"{reverse('dashboard:overview')}?section=staff")

        if action == 'create_category':
            category_form = MenuCategoryForm(request.POST)
            if category_form.is_valid():
                category_form.save()
                messages.success(request, 'Category created.')
            else:
                messages.error(request, 'Invalid category data.')
            return redirect(f"{reverse('dashboard:overview')}?section=categories")

        if action == 'update_category':
            category = get_object_or_404(MenuCategory, id=request.POST.get('category_id'))
            category.name = request.POST.get('name', category.name)
            category.display_order = int(request.POST.get('display_order') or category.display_order)
            category.save(update_fields=['name', 'display_order'])
            messages.success(request, 'Category updated.')
            return redirect(f"{reverse('dashboard:overview')}?section=categories")

        if action == 'delete_category':
            category = get_object_or_404(MenuCategory, id=request.POST.get('category_id'))
            category.delete()
            messages.success(request, 'Category deleted.')
            return redirect(f"{reverse('dashboard:overview')}?section=categories")

        if action == 'create_item':
            item_form = MenuItemForm(request.POST)
            if item_form.is_valid():
                item_form.save()
                messages.success(request, 'Menu item created.')
            else:
                messages.error(request, 'Invalid menu item data.')
            return redirect(f"{reverse('dashboard:overview')}?section=menus")

        if action == 'update_item':
            item = get_object_or_404(MenuItem, id=request.POST.get('item_id'))
            item.name = request.POST.get('name', item.name)
            item.description = request.POST.get('description', item.description)
            item.image_url = request.POST.get('image_url', item.image_url)
            item.price = Decimal(request.POST.get('price') or item.price)
            item.available = request.POST.get('available') == 'on'
            item.save(update_fields=['name', 'description', 'image_url', 'price', 'available'])
            messages.success(request, 'Menu item updated.')
            return redirect(f"{reverse('dashboard:overview')}?section=menus")

        if action == 'delete_item':
            item = get_object_or_404(MenuItem, id=request.POST.get('item_id'))
            item.delete()
            messages.success(request, 'Menu item deleted.')
            return redirect(f"{reverse('dashboard:overview')}?section=menus")

        if action == 'toggle_item_availability':
            item = get_object_or_404(MenuItem, id=request.POST.get('item_id'))
            item.available = not item.available
            item.save(update_fields=['available'])
            messages.success(request, f'Item {item.name} availability updated.')
            return redirect(f"{reverse('dashboard:overview')}?section=menus")

        if action == 'generate_tables':
            table_form = TableGenerateForm(request.POST)
            if table_form.is_valid():
                restaurant = table_form.cleaned_data['restaurant']
                table_count = table_form.cleaned_data['table_count']
                existing_numbers = set(Table.objects.filter(restaurant=restaurant).values_list('table_number', flat=True))
                created = 0
                for number in range(1, table_count + 1):
                    if number not in existing_numbers:
                        Table.objects.create(
                            restaurant=restaurant,
                            table_number=number,
                            qr_token=generate_qr_token(),
                            verification_pin=generate_table_pin(),
                        )
                        created += 1
                messages.success(request, f'Generated/ensured tables up to {table_count}. New created: {created}.')
            else:
                messages.error(request, 'Invalid table generation input.')
            return redirect(f"{reverse('dashboard:overview')}?section=tables")

        if action == 'add_table':
            restaurant_id = request.POST.get('restaurant_id')
            table_number = int(request.POST.get('table_number') or 0)
            restaurant = get_object_or_404(Restaurant, id=restaurant_id)
            if table_number <= 0:
                messages.error(request, 'Table number must be greater than zero.')
            else:
                Table.objects.get_or_create(
                    restaurant=restaurant,
                    table_number=table_number,
                    defaults={'qr_token': generate_qr_token(), 'verification_pin': generate_table_pin()},
                )
                messages.success(request, 'Table added/exists already.')
            return redirect(f"{reverse('dashboard:overview')}?section=tables")

        if action == 'update_table':
            table = get_object_or_404(Table, id=request.POST.get('table_id'))
            table.table_number = int(request.POST.get('table_number') or table.table_number)
            table.status = request.POST.get('status', table.status)
            table.qr_enabled = request.POST.get('qr_enabled') == 'on'
            table.is_active = request.POST.get('is_active') == 'on'
            table.save(update_fields=['table_number', 'status', 'qr_enabled', 'is_active'])
            messages.success(request, 'Table updated.')
            return redirect(f"{reverse('dashboard:overview')}?section=tables")

        if action == 'regenerate_qr':
            table = get_object_or_404(Table, id=request.POST.get('table_id'))
            table.qr_token = generate_qr_token()
            table.verification_pin = generate_table_pin()
            table.save(update_fields=['qr_token', 'verification_pin'])
            messages.success(request, 'QR token regenerated for table.')
            return redirect(f"{reverse('dashboard:overview')}?section=qr")

        if action == 'cancel_order':
            session = get_object_or_404(OrderSession, id=request.POST.get('session_id'))
            session.status = OrderSession.Status.CANCELLED
            session.closed_at = timezone.now()
            session.table.status = Table.Status.FREE
            session.table.save(update_fields=['status'])
            session.save(update_fields=['status', 'closed_at'])
            messages.success(request, f'Session #{session.id} canceled.')
            return redirect(f"{reverse('dashboard:overview')}?section=orders")

        if action == 'update_order_status':
            item = get_object_or_404(OrderItem, id=request.POST.get('order_item_id'))
            next_status = request.POST.get('status')
            valid = {x for x, _ in OrderItem.Status.choices}
            if next_status in valid:
                item.status = next_status
                item.save(update_fields=['status'])
                messages.success(request, f'Order item #{item.id} updated to {item.status}.')
            else:
                messages.error(request, 'Invalid status.')
            return redirect(f"{reverse('dashboard:overview')}?section=orders")

    staff_form = StaffUserCreateForm()
    table_form = TableGenerateForm()
    category_form = MenuCategoryForm()
    item_form = MenuItemForm()

    today = timezone.localdate()
    orders_today = OrderSession.objects.filter(created_at__date=today)
    payments_today = PaymentTransaction.objects.filter(status=PaymentTransaction.Status.PAID, created_at__date=today)
    total_orders_today = orders_today.count()
    total_revenue_today = payments_today.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_customers = OrderSession.objects.exclude(customer_name='').values('customer_name').distinct().count()
    active_tables = Table.objects.filter(status=Table.Status.ACTIVE).count()
    pending_orders = OrderItem.objects.filter(status=OrderItem.Status.ORDERED).count()
    popular_items = (
        OrderItem.objects.values('menu_item__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )

    categories = MenuCategory.objects.select_related('restaurant').order_by('restaurant__name', 'display_order', 'name')
    menu_items = MenuItem.objects.select_related('restaurant', 'category').order_by('restaurant__name', 'category__name', 'name')
    tables = Table.objects.select_related('restaurant').order_by('restaurant__name', 'table_number')

    staff_users = User.objects.filter(is_staff=True).select_related('employee_profile').order_by('username')

    order_sessions = OrderSession.objects.select_related('table', 'table__restaurant').order_by('-created_at')[:200]
    order_items = OrderItem.objects.select_related('session', 'session__table', 'menu_item').order_by('-created_at')[:300]

    payment_records = PaymentTransaction.objects.select_related('session', 'session__table').order_by('-created_at')[:300]
    payment_pending_sessions = OrderSession.objects.select_related('table').filter(status=OrderSession.Status.PAYMENT_REQUESTED)

    report_type = request.GET.get('report_type', 'daily')
    start_date, end_date = _report_window(report_type)
    report_payments = PaymentTransaction.objects.filter(
        status=PaymentTransaction.Status.PAID,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )
    report_total = report_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    report_most_selling = (
        OrderItem.objects.filter(session__created_at__date__gte=start_date, session__created_at__date__lte=end_date)
        .values('menu_item__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:10]
    )
    report_peak_hours = (
        OrderSession.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        .annotate(hour=ExtractHour('created_at'))
        .values('hour')
        .annotate(cnt=Count('id'))
        .order_by('-cnt', 'hour')[:5]
    )
    report_daily_series = (
        report_payments.annotate(day=TruncDate('created_at')).values('day').annotate(total=Sum('amount')).order_by('day')
    )

    qr_tables = (
        Table.objects.select_related('restaurant')
        .annotate(qr_orders=Count('sessions'))
        .order_by('restaurant__name', 'table_number')
    )

    new_user_credentials = request.session.pop('new_user_credentials', None)

    context = {
        'section': section,
        'staff_form': staff_form,
        'table_form': table_form,
        'category_form': category_form,
        'item_form': item_form,
        'restaurants': Restaurant.objects.filter(is_active=True).order_by('name'),
        'today_stats': {
            'total_orders_today': total_orders_today,
            'total_revenue_today': total_revenue_today,
            'total_customers': total_customers,
            'active_tables': active_tables,
            'pending_orders': pending_orders,
        },
        'popular_items': popular_items,
        'categories': categories,
        'menu_items': menu_items,
        'tables': tables,
        'table_status_choices': Table.Status.choices,
        'staff_users': staff_users,
        'order_sessions': order_sessions,
        'order_items': order_items,
        'payment_records': payment_records,
        'payment_pending_sessions': payment_pending_sessions,
        'report_type': report_type,
        'report_total': report_total,
        'report_start': start_date,
        'report_end': end_date,
        'report_most_selling': report_most_selling,
        'report_peak_hours': report_peak_hours,
        'report_daily_series': report_daily_series,
        'qr_tables': qr_tables,
        'new_user_credentials': new_user_credentials,
    }
    return render(request, 'dashboard/overview.html', context)


@login_required
@user_passes_test(_is_admin_user)
def staff_user_detail(request, user_id: int):
    user = get_object_or_404(User.objects.select_related('employee_profile'), id=user_id, is_staff=True)
    sessions = OrderSession.objects.filter(confirmed_by=user).order_by('-created_at')[:50]
    return render(
        request,
        'dashboard/user_detail.html',
        {
            'staff_user': user,
            'profile': getattr(user, 'employee_profile', None),
            'sessions': sessions,
        },
    )


@login_required
@user_passes_test(_is_admin_user)
def payment_detail(request, payment_id: int):
    payment = get_object_or_404(
        PaymentTransaction.objects.select_related('session', 'session__table', 'session__table__restaurant'),
        id=payment_id,
    )
    return render(
        request,
        'dashboard/payment_detail.html',
        {
            'payment': payment,
            'session': payment.session,
            'items': payment.session.items.select_related('menu_item').all(),
        },
    )


@login_required
@user_passes_test(_is_admin_or_cashier_user)
def session_bill_print(request, session_id: int):
    session = get_object_or_404(
        OrderSession.objects.select_related('table', 'table__restaurant'),
        id=session_id,
    )
    items = session.items.select_related('menu_item').all()
    return render(
        request,
        'dashboard/print_bill.html',
        {
            'session': session,
            'items': items,
        },
    )


@login_required
@user_passes_test(_is_admin_user)
def report_export_csv(request):
    report_type = request.GET.get('report_type', 'daily')
    start_date, end_date = _report_window(report_type)

    payments = PaymentTransaction.objects.select_related('session', 'session__table').filter(
        status=PaymentTransaction.Status.PAID,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_sales_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Payment ID', 'Session', 'Table', 'Method', 'Amount', 'Status', 'Created At'])
    for p in payments:
        writer.writerow([p.id, p.session_id, p.session.table.table_number if p.session_id else '', p.method, p.amount, p.status, p.created_at])
    return response


@login_required
@user_passes_test(_is_admin_user)
def report_export_pdf(request):
    report_type = request.GET.get('report_type', 'daily')
    start_date, end_date = _report_window(report_type)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception:
        return HttpResponse('PDF library unavailable. Install reportlab.', status=500)

    payments = PaymentTransaction.objects.filter(
        status=PaymentTransaction.Status.PAID,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )
    total = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_sales_report.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    y = 800
    p.drawString(40, y, f'{report_type.title()} Sales Report')
    y -= 20
    p.drawString(40, y, f'From {start_date} to {end_date}')
    y -= 20
    p.drawString(40, y, f'Total Revenue: {total}')
    y -= 30
    p.drawString(40, y, 'Payments:')
    y -= 20
    for pay in payments[:100]:
        p.drawString(50, y, f'#{pay.id} | {pay.method} | {pay.amount} | {pay.created_at}')
        y -= 16
        if y < 60:
            p.showPage()
            y = 800
    p.showPage()
    p.save()
    return response
