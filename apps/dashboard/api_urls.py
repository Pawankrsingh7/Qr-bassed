from django.urls import path

from .api_views import (
    AdminOverviewAPIView,
    ManualSessionCloseAPIView,
    MenuCategoryListCreateAPIView,
    MenuItemDetailAPIView,
    MenuItemListCreateAPIView,
    SessionHistoryAPIView,
    TableStatusAPIView,
)

app_name = 'dashboard_api'

urlpatterns = [
    path('overview/', AdminOverviewAPIView.as_view(), name='overview'),
    path('sessions/history/', SessionHistoryAPIView.as_view(), name='session-history'),
    path('sessions/<int:session_id>/manual-close/', ManualSessionCloseAPIView.as_view(), name='manual-close-session'),
    path('tables/status/', TableStatusAPIView.as_view(), name='table-status'),
    path('menu/categories/', MenuCategoryListCreateAPIView.as_view(), name='menu-categories'),
    path('menu/items/', MenuItemListCreateAPIView.as_view(), name='menu-items'),
    path('menu/items/<int:item_id>/', MenuItemDetailAPIView.as_view(), name='menu-item-detail'),
]
