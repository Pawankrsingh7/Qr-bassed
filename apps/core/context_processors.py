from .roles import ROLE_ADMIN, ROLE_CASHIER, ROLE_KITCHEN, ROLE_WAITER, get_role_home_url, get_user_role


def auth_role_context(request):
    role = get_user_role(request.user)
    return {
        'auth_role': role,
        'role_home_url': get_role_home_url(request.user),
        'is_admin_role': role == ROLE_ADMIN,
        'is_kitchen_role': role == ROLE_KITCHEN,
        'is_cashier_role': role == ROLE_CASHIER,
        'is_waiter_role': role == ROLE_WAITER,
    }
