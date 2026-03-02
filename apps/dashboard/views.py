from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.menu.models import MenuCategory, MenuItem
from apps.orders.models import OrderSession
from apps.tables.models import Table
from apps.tables.utils import generate_qr_token, generate_table_pin

from .forms import MenuCategoryForm, MenuItemForm, StaffUserCreateForm, TableGenerateForm


def _is_staff_user(user):
    return bool(user and user.is_authenticated and user.is_staff)


@login_required
@user_passes_test(_is_staff_user)
def admin_dashboard(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_staff':
            staff_form = StaffUserCreateForm(request.POST)
            if staff_form.is_valid():
                staff_form.save()
                messages.success(request, 'Staff user created successfully.')
                return redirect('dashboard:overview')
            messages.error(request, 'Could not create staff user. Check form values.')

        elif action == 'generate_tables':
            table_form = TableGenerateForm(request.POST)
            if table_form.is_valid():
                restaurant = table_form.cleaned_data['restaurant']
                table_count = table_form.cleaned_data['table_count']

                existing_numbers = set(
                    Table.objects.filter(restaurant=restaurant).values_list('table_number', flat=True)
                )
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

                messages.success(
                    request,
                    f'Table generation completed. Requested: {table_count}, newly created: {created}.',
                )
                return redirect('dashboard:overview')
            messages.error(request, 'Invalid table generation input.')

        elif action == 'create_category':
            category_form = MenuCategoryForm(request.POST)
            if category_form.is_valid():
                category_form.save()
                messages.success(request, 'Menu category created.')
                return redirect('dashboard:overview')
            messages.error(request, 'Invalid category input.')

        elif action == 'create_item':
            item_form = MenuItemForm(request.POST)
            if item_form.is_valid():
                item_form.save()
                messages.success(request, 'Menu item created.')
                return redirect('dashboard:overview')
            messages.error(request, 'Invalid menu item input.')

    staff_form = StaffUserCreateForm()
    table_form = TableGenerateForm()
    category_form = MenuCategoryForm()
    item_form = MenuItemForm()

    table_queryset = Table.objects.select_related('restaurant').order_by('restaurant__name', 'table_number')
    total_tables = table_queryset.count()
    free_tables = table_queryset.filter(status=Table.Status.FREE).count()
    active_tables = table_queryset.filter(status=Table.Status.ACTIVE).count()
    paid_tables = table_queryset.filter(status=Table.Status.PAID).count()

    total_revenue = (
        OrderSession.objects.filter(payment_status=OrderSession.PaymentStatus.PAID).aggregate(total=Sum('total_amount'))['total']
        or 0
    )

    tables = []
    for table in table_queryset:
        tables.append(
            {
                'id': table.id,
                'restaurant': table.restaurant.name,
                'table_number': table.table_number,
                'status': table.status,
                'pin': table.verification_pin,
                'scan_path': reverse(
                    'core:scan-order',
                    kwargs={
                        'restaurant_slug': table.restaurant.slug,
                        'table_number': table.table_number,
                        'qr_token': table.qr_token,
                    },
                ),
                'qr_svg_path': reverse(
                    'tables_web:table-qr-svg',
                    kwargs={
                        'restaurant_slug': table.restaurant.slug,
                        'table_number': table.table_number,
                        'qr_token': table.qr_token,
                    },
                ),
            }
        )

    context = {
        'staff_form': staff_form,
        'table_form': table_form,
        'category_form': category_form,
        'item_form': item_form,
        'staff_users': User.objects.filter(is_staff=True).order_by('username'),
        'categories': MenuCategory.objects.select_related('restaurant').order_by('restaurant__name', 'display_order', 'name'),
        'menu_items': MenuItem.objects.select_related('restaurant', 'category').order_by('restaurant__name', 'name'),
        'tables': tables,
        'total_tables': total_tables,
        'free_tables': free_tables,
        'active_tables': active_tables,
        'paid_tables': paid_tables,
        'total_revenue': total_revenue,
    }
    return render(request, 'dashboard/overview.html', context)
