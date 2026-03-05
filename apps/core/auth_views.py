from django.contrib.auth.views import LoginView

from .roles import get_role_home_url


class RoleBasedLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        return get_role_home_url(self.request.user)
