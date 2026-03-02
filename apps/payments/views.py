from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsStaffUser
from apps.orders.models import OrderSession

from .services import mark_cash_payment


class CashPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class CashPaymentAPIView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, session_id: int):
        session = get_object_or_404(OrderSession, id=session_id)
        serializer = CashPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = mark_cash_payment(session, serializer.validated_data['amount'])
        session.refresh_from_db()

        return Response(
            {
                'message': 'Cash payment recorded and session closed.',
                'payment_id': payment.id,
                'session_id': session.id,
                'session_status': session.status,
                'payment_status': session.payment_status,
            },
            status=status.HTTP_200_OK,
        )
