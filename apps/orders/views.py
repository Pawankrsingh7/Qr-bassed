import json

from django.shortcuts import get_object_or_404, render
from django.db.models import Count
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsStaffUser
from apps.menu.models import MenuCategory
from apps.tables.models import Table

from .models import OrderSession
from .serializers import (
    AddOrderItemsSerializer,
    OrderSessionSerializer,
    SessionBootstrapSerializer,
)
from .services import add_items_to_session, confirm_session, get_or_create_open_session, request_bill


def customer_order_page(request, restaurant_slug: str, table_number: int, qr_token: str):
    table = get_object_or_404(
        Table,
        restaurant__slug=restaurant_slug,
        table_number=table_number,
        qr_token=qr_token,
        is_active=True,
        qr_enabled=True,
    )
    categories = MenuCategory.objects.filter(restaurant=table.restaurant).prefetch_related('items')
    menu_payload = []
    for category in categories:
        menu_payload.append(
            {
                'id': category.id,
                'name': category.name,
                'items': [
                    {
                        'id': item.id,
                        'name': item.name,
                        'description': item.description,
                        'image_url': item.image_url,
                        'price': str(item.price),
                        'available': item.available,
                    }
                    for item in category.items.all()
                ],
            }
        )

    context = {
        'restaurant_slug': restaurant_slug,
        'table_number': table.table_number,
        'qr_token': qr_token,
        'menu_payload_json': json.dumps(menu_payload),
        'message': f'Scan successful for {table.restaurant.name}. Place your order.',
    }
    return render(request, 'customer/order_page.html', context)


class SessionBootstrapAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SessionBootstrapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        table = get_object_or_404(
            Table,
            restaurant__slug=serializer.validated_data['restaurant_slug'],
            table_number=serializer.validated_data['table_number'],
            is_active=True,
        )
        if table.status == Table.Status.RESERVED:
            return Response({'detail': 'This table is currently reserved.'}, status=status.HTTP_403_FORBIDDEN)

        provided_pin = serializer.validated_data.get('verification_pin') or ''
        provided_token = serializer.validated_data.get('qr_token') or ''

        if not provided_pin and not provided_token:
            return Response({'detail': 'verification_pin or qr_token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if provided_token and provided_token == table.qr_token:
            pass
        elif provided_pin and provided_pin == table.verification_pin:
            pass
        else:
            return Response({'detail': 'Invalid table verification details.'}, status=status.HTTP_403_FORBIDDEN)

        session = get_or_create_open_session(
            table=table,
            force_new_session=serializer.validated_data['force_new_session'],
            customer_name=serializer.validated_data.get('customer_name', ''),
        )

        return Response(
            {
                'message': 'Session ready',
                'session': OrderSessionSerializer(session).data,
            },
            status=status.HTTP_200_OK,
        )


class AddOrderItemsAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, session_id: int):
        session = get_object_or_404(OrderSession, id=session_id)
        serializer = AddOrderItemsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        add_items_to_session(session=session, payload_items=serializer.validated_data['items'])
        session.refresh_from_db()

        waiting_confirmation = session.status == OrderSession.Status.PENDING_CONFIRMATION
        response_message = 'Waiting for staff confirmation.' if waiting_confirmation else 'Order placed.'

        return Response(
            {
                'message': response_message,
                'session': OrderSessionSerializer(session).data,
                'requires_staff_confirmation': waiting_confirmation,
            },
            status=status.HTTP_201_CREATED,
        )


class SessionDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, session_id: int):
        session = get_object_or_404(OrderSession, id=session_id)
        return Response(OrderSessionSerializer(session).data)


class SessionRequestBillAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, session_id: int):
        session = get_object_or_404(OrderSession, id=session_id)
        session = request_bill(session)
        return Response(
            {
                'message': 'Bill requested successfully.',
                'session': OrderSessionSerializer(session).data,
            }
        )


class SessionConfirmAPIView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, session_id: int):
        session = get_object_or_404(OrderSession, id=session_id)
        session = confirm_session(session=session, user=request.user if request.user.is_authenticated else None)

        return Response(
            {
                'message': 'Session confirmed.',
                'session': OrderSessionSerializer(session).data,
            }
        )


class TableOpenSessionAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        restaurant_slug = request.query_params.get('restaurant_slug')
        table_number = request.query_params.get('table_number')
        if not restaurant_slug or not table_number:
            return Response({'detail': 'restaurant_slug and table_number are required.'}, status=400)

        table = get_object_or_404(
            Table,
            restaurant__slug=restaurant_slug,
            table_number=table_number,
            is_active=True,
        )
        session = table.sessions.filter(
            status__in=[
                OrderSession.Status.PENDING_CONFIRMATION,
                OrderSession.Status.ACTIVE,
                OrderSession.Status.PAYMENT_REQUESTED,
            ]
        ).first()

        if not session:
            return Response({'session': None})
        return Response({'session': OrderSessionSerializer(session).data})


class CustomerMenuAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        restaurant_slug = request.query_params.get('restaurant_slug')
        if not restaurant_slug:
            return Response({'detail': 'restaurant_slug is required.'}, status=400)

        categories = MenuCategory.objects.filter(restaurant__slug=restaurant_slug).prefetch_related('items')
        data = []
        for category in categories:
            items = [
                {
                    'id': item.id,
                    'name': item.name,
                    'description': item.description,
                    'image_url': item.image_url,
                    'price': str(item.price),
                    'available': item.available,
                }
                for item in category.items.all()
            ]
            data.append({'id': category.id, 'name': category.name, 'items': items})

        return Response({'categories': data})


class PendingConfirmationsAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        pending_sessions = (
            OrderSession.objects.select_related('table', 'table__restaurant')
            .filter(status=OrderSession.Status.PENDING_CONFIRMATION)
            .annotate(item_count=Count('items'))
            .filter(item_count__gt=0)
        )
        payload = [
            {
                'session_id': session.id,
                'restaurant': session.table.restaurant.name,
                'table_number': session.table.table_number,
                'customer_name': session.customer_name or 'Guest',
                'created_at': session.created_at,
                'total_amount': session.total_amount,
            }
            for session in pending_sessions
        ]
        return Response({'pending_confirmations': payload})
