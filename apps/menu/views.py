from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.restaurants.models import Restaurant

from .models import MenuCategory


class RestaurantMenuAPIView(APIView):
    def get(self, request, restaurant_slug: str):
        restaurant = get_object_or_404(Restaurant, slug=restaurant_slug, is_active=True)
        categories = MenuCategory.objects.filter(restaurant=restaurant).prefetch_related('items')

        payload = []
        for category in categories:
            payload.append(
                {
                    'id': category.id,
                    'name': category.name,
                    'items': [
                        {
                            'id': item.id,
                            'name': item.name,
                            'description': item.description,
                            'price': str(item.price),
                            'available': item.available,
                        }
                        for item in category.items.all()
                    ],
                }
            )

        return Response({'restaurant': restaurant.name, 'categories': payload})
