from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsStaffUser
from apps.menu.models import MenuCategory, MenuItem
from apps.orders.models import OrderSession
from apps.tables.models import Table


class MenuCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuCategory
        fields = ('id', 'restaurant', 'name', 'display_order')


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ('id', 'restaurant', 'category', 'name', 'description', 'price', 'available')


class AdminOverviewAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        active_sessions = OrderSession.objects.filter(
            status__in=[
                OrderSession.Status.PENDING_CONFIRMATION,
                OrderSession.Status.ACTIVE,
                OrderSession.Status.PAYMENT_REQUESTED,
            ]
        )

        revenue = (
            OrderSession.objects.filter(payment_status=OrderSession.PaymentStatus.PAID).aggregate(total=Sum('total_amount'))['total']
            or 0
        )

        return Response(
            {
                'active_tables': Table.objects.filter(status=Table.Status.ACTIVE).count(),
                'pending_confirmations': active_sessions.filter(status=OrderSession.Status.PENDING_CONFIRMATION).count(),
                'payment_requested': active_sessions.filter(status=OrderSession.Status.PAYMENT_REQUESTED).count(),
                'total_revenue': revenue,
            }
        )


class SessionHistoryAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        sessions = OrderSession.objects.select_related('table', 'table__restaurant').order_by('-created_at')[:100]
        data = [
            {
                'id': session.id,
                'restaurant': session.table.restaurant.name,
                'table_number': session.table.table_number,
                'status': session.status,
                'payment_status': session.payment_status,
                'total_amount': session.total_amount,
                'created_at': session.created_at,
                'closed_at': session.closed_at,
            }
            for session in sessions
        ]
        return Response({'sessions': data})


class TableStatusAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        restaurant_slug = request.query_params.get('restaurant_slug')
        tables = Table.objects.select_related('restaurant').order_by('restaurant__name', 'table_number')
        if restaurant_slug:
            tables = tables.filter(restaurant__slug=restaurant_slug)

        payload = [
            {
                'table_id': table.id,
                'restaurant': table.restaurant.name,
                'table_number': table.table_number,
                'status': table.status,
                'verification_pin': table.verification_pin,
                'is_active': table.is_active,
            }
            for table in tables
        ]
        return Response({'tables': payload})


class ManualSessionCloseAPIView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, session_id: int):
        session = get_object_or_404(OrderSession, id=session_id)
        if session.status in (OrderSession.Status.CLOSED, OrderSession.Status.CANCELLED):
            return Response({'message': 'Session already closed.', 'session_id': session.id})

        session.status = OrderSession.Status.CANCELLED
        session.table.status = Table.Status.FREE
        session.table.save(update_fields=['status'])
        session.save(update_fields=['status'])
        return Response({'message': 'Session closed manually.', 'session_id': session.id})


class MenuCategoryListCreateAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        categories = MenuCategory.objects.select_related('restaurant').order_by('restaurant__name', 'display_order', 'name')
        return Response(MenuCategorySerializer(categories, many=True).data)

    def post(self, request):
        serializer = MenuCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MenuItemListCreateAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        items = MenuItem.objects.select_related('restaurant', 'category').order_by('restaurant__name', 'category__name', 'name')
        return Response(MenuItemSerializer(items, many=True).data)

    def post(self, request):
        serializer = MenuItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MenuItemDetailAPIView(APIView):
    permission_classes = [IsStaffUser]

    def put(self, request, item_id: int):
        item = get_object_or_404(MenuItem, id=item_id)
        serializer = MenuItemSerializer(item, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, item_id: int):
        item = get_object_or_404(MenuItem, id=item_id)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
