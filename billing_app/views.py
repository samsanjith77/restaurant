from rest_framework import generics
from .models import Dish, Order
from .serializers import DishSerializer, OrderSerializer


# List all dishes
class DishListView(generics.ListAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer


# Create order
class OrderCreateView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


# Get last 5 orders
class LastOrdersView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.all().order_by('-created_at')[:5]
