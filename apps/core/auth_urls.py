from django.contrib.auth.views import LogoutView
from django.urls import path

from .auth_views import RoleBasedLoginView

urlpatterns = [
    path('login/', RoleBasedLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(template_name='registration/logged_out.html'), name='logout'),
]
