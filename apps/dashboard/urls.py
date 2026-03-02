from django.urls import path

from .views import admin_dashboard

app_name = 'dashboard'

urlpatterns = [
    path('', admin_dashboard, name='overview'),
]
