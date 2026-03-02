from django.urls import path

from .views import CashPaymentAPIView

app_name = 'payments_api'

urlpatterns = [
    path('sessions/<int:session_id>/cash/', CashPaymentAPIView.as_view(), name='cash-payment'),
]
