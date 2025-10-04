from rest_framework import serializers
from .models import Dish, Order, OrderItem


class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = ['id', 'name', 'price', 'image']


class OrderItemSerializer(serializers.ModelSerializer):
    dish = DishSerializer(read_only=True)
    dish_id = serializers.PrimaryKeyRelatedField(
        queryset=Dish.objects.all(), source="dish", write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'dish', 'dish_id', 'quantity', 'price']
        read_only_fields = ['price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Order
        fields = ['id', 'created_at', 'total_amount', 'items']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        frontend_total = validated_data['total_amount']  # total sent from frontend
        order = Order.objects.create(total_amount=0)

        backend_total = 0
        for item in items_data:
            dish = item['dish']
            quantity = item['quantity']
            price = dish.price * quantity
            backend_total += price

        # Compare frontend and backend totals
        if frontend_total != backend_total:
            raise serializers.ValidationError(
                {"total_amount": f"Mismatch! Frontend sent {frontend_total}, backend calculated {backend_total}"}
            )

        # Save items since total matches
        for item in items_data:
            dish = item['dish']
            quantity = item['quantity']
            price = dish.price * quantity
            OrderItem.objects.create(
                order=order,
                dish=dish,
                quantity=quantity,
                price=price
            )

        order.total_amount = backend_total
        order.save()
        return order
