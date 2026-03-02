from django.urls import path

from .views import (
    AddOrderItemsAPIView,
    CustomerMenuAPIView,
    PendingConfirmationsAPIView,
    SessionBootstrapAPIView,
    SessionConfirmAPIView,
    SessionDetailAPIView,
    SessionRequestBillAPIView,
    TableOpenSessionAPIView,
)

app_name = 'orders_api'

urlpatterns = [
    path('menu/', CustomerMenuAPIView.as_view(), name='customer-menu'),
    path('sessions/bootstrap/', SessionBootstrapAPIView.as_view(), name='session-bootstrap'),
    path('sessions/open/', TableOpenSessionAPIView.as_view(), name='table-open-session'),
    path('sessions/<int:session_id>/', SessionDetailAPIView.as_view(), name='session-detail'),
    path('sessions/<int:session_id>/items/', AddOrderItemsAPIView.as_view(), name='add-order-items'),
    path('sessions/<int:session_id>/confirm/', SessionConfirmAPIView.as_view(), name='session-confirm'),
    path('sessions/<int:session_id>/request-bill/', SessionRequestBillAPIView.as_view(), name='session-request-bill'),
    path('sessions/pending-confirmations/', PendingConfirmationsAPIView.as_view(), name='pending-confirmations'),
]
