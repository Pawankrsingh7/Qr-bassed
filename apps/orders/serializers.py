from rest_framework import serializers

from .models import OrderItem, OrderSession


class OrderItemInputSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class SessionBootstrapSerializer(serializers.Serializer):
    restaurant_slug = serializers.SlugField()
    table_number = serializers.IntegerField(min_value=1)
    verification_pin = serializers.CharField(max_length=4, required=False, allow_blank=True)
    qr_token = serializers.CharField(max_length=64, required=False, allow_blank=True)
    force_new_session = serializers.BooleanField(default=False)


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'menu_item', 'menu_item_name', 'quantity', 'price', 'status', 'created_at')


class OrderSessionSerializer(serializers.ModelSerializer):
    table_number = serializers.IntegerField(source='table.table_number', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = OrderSession
        fields = (
            'id',
            'table_number',
            'status',
            'payment_status',
            'total_amount',
            'created_at',
            'confirmed_at',
            'items',
        )


class AddOrderItemsSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('At least one item is required.')
        return value
