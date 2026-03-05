from django.contrib.auth.models import AnonymousUser


ROLE_ADMIN = 'admin'
ROLE_KITCHEN = 'kitchen'
ROLE_WAITER = 'waiter'
ROLE_CASHIER = 'cashier'


def get_user_role(user):
    if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
        return None
    cached = getattr(user, '_cached_role', None)
    if cached:
        return cached

    if user.is_superuser:
        user._cached_role = ROLE_ADMIN
        return ROLE_ADMIN

    group_names = set(user.groups.values_list('name', flat=True))
    if 'admin' in group_names or 'manager' in group_names:
        user._cached_role = ROLE_ADMIN
        return ROLE_ADMIN
    if 'kitchen' in group_names:
        user._cached_role = ROLE_KITCHEN
        return ROLE_KITCHEN
    if 'cashier' in group_names:
        user._cached_role = ROLE_CASHIER
        return ROLE_CASHIER
    if 'waiter' in group_names or 'staff' in group_names:
        user._cached_role = ROLE_WAITER
        return ROLE_WAITER
    if user.is_staff:
        user._cached_role = ROLE_ADMIN
        return ROLE_ADMIN
    user._cached_role = None
    return None


def get_role_home_url(user):
    role = get_user_role(user)
    if role == ROLE_ADMIN:
        return '/dashboard/'
    if role == ROLE_KITCHEN:
        return '/kitchen/'
    if role == ROLE_CASHIER:
        return '/cashier/'
    if role == ROLE_WAITER:
        return '/staff/'
    return '/'
