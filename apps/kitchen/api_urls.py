from django.urls import path

from .api_views import (
    KitchenConfirmSessionAPIView,
    KitchenOrderItemStatusAPIView,
    KitchenPendingConfirmationsAPIView,
    KitchenQueueAPIView,
)

app_name = 'kitchen_api'

urlpatterns = [
    path('queue/', KitchenQueueAPIView.as_view(), name='queue'),
    path('order-items/<int:item_id>/status/', KitchenOrderItemStatusAPIView.as_view(), name='item-status'),
    path('pending-confirmations/', KitchenPendingConfirmationsAPIView.as_view(), name='pending-confirmations'),
    path('sessions/<int:session_id>/confirm/', KitchenConfirmSessionAPIView.as_view(), name='confirm-session'),
]
