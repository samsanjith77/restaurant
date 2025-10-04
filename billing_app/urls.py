from django.urls import path
from .views import DishListView, OrderCreateView, LastOrdersView

urlpatterns = [
    path('dishes/', DishListView.as_view(), name='dish-list'),
    path('orders/', OrderCreateView.as_view(), name='order-create'),
    path('orders/last/', LastOrdersView.as_view(), name='last-orders'),
]
