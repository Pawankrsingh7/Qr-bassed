from django.urls import path

from .views import RestaurantMenuAPIView

app_name = 'menu_api'

urlpatterns = [
    path('restaurants/<slug:restaurant_slug>/', RestaurantMenuAPIView.as_view(), name='restaurant-menu'),
]
