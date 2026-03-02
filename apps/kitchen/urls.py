from django.urls import path

from .views import kitchen_dashboard

app_name = 'kitchen'

urlpatterns = [
    path('', kitchen_dashboard, name='dashboard'),
]
