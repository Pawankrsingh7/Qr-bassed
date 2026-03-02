from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsStaffUser
from apps.orders.models import OrderItem, OrderSession
from apps.orders.serializers import OrderSessionSerializer
from apps.orders.services import confirm_session


class KitchenQueueAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        items = OrderItem.objects.select_related('session', 'session__table', 'menu_item').filter(
            session__status__in=[
                OrderSession.Status.PENDING_CONFIRMATION,
                OrderSession.Status.ACTIVE,
                OrderSession.Status.PAYMENT_REQUESTED,
            ],
            status__in=[OrderItem.Status.ORDERED, OrderItem.Status.PREPARING, OrderItem.Status.READY],
        )
        payload = [
            {
                'id': item.id,
                'session_id': item.session_id,
                'session_status': item.session.status,
                'table_number': item.session.table.table_number,
                'menu_item': item.menu_item.name,
                'quantity': item.quantity,
                'status': item.status,
                'created_at': item.created_at,
            }
            for item in items
        ]
        return Response({'orders': payload})


class KitchenOrderItemStatusAPIView(APIView):
    permission_classes = [IsStaffUser]

    def patch(self, request, item_id: int):
        item = get_object_or_404(OrderItem, id=item_id)
        next_status = request.data.get('status')
        valid_statuses = {choice for choice, _ in OrderItem.Status.choices}

        if next_status not in valid_statuses:
            return Response({'detail': 'Invalid status.'}, status=400)

        item.status = next_status
        item.save(update_fields=['status'])
        return Response({'message': 'Order item status updated.', 'item_id': item.id, 'status': item.status})


class KitchenPendingConfirmationsAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        sessions = OrderSession.objects.select_related('table', 'table__restaurant').filter(
            status=OrderSession.Status.PENDING_CONFIRMATION
        )
        data = [
            {
                'session_id': session.id,
                'restaurant': session.table.restaurant.name,
                'table_number': session.table.table_number,
                'created_at': session.created_at,
                'total_amount': session.total_amount,
            }
            for session in sessions
        ]
        return Response({'pending_confirmations': data})


class KitchenConfirmSessionAPIView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, session_id: int):
        session = get_object_or_404(OrderSession, id=session_id)
        confirmed = confirm_session(session=session, user=request.user)
        return Response({'message': 'Session confirmed.', 'session': OrderSessionSerializer(confirmed).data})
