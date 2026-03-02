from django.urls import path

from .views import TableListAPIView

app_name = 'tables_api'

urlpatterns = [
    path('restaurants/<slug:restaurant_slug>/', TableListAPIView.as_view(), name='table-list'),
]
