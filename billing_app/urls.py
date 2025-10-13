from django.urls import path

from .views import *
urlpatterns = [
    path('dishes/', DishListView.as_view(), name='dish-list'),
    path('dishes/<int:dish_id>/', DishDetailView.as_view(), name='dish-detail'),
    path('orders/create/', CreateOrderView.as_view(), name='order-create'),
    path('orders/history/', OrderHistoryView.as_view(), name='last-orders'),
    path('dish_sales/', dish_sales_in_period, name='dish_sales_in_period'),
    # New Dish Management URLs
    path('dishes/create/', CreateDishView.as_view(), name='dish-create'),
    path('dishes/<int:dish_id>/update-image/', UpdateDishImageView.as_view(), name='dish-update-image'),
    path('dishes/<int:dish_id>/update-price/', UpdateDishPriceView.as_view(), name='dish-update-price'),
    # expenditure
    path('persons/', PersonListView.as_view(), name='persons'),
    path('expenses/filter/', ExpenseFilterView.as_view(), name='expenses_filter'),
    path('persons/add/', PersonCreateView.as_view(), name='add_person'),
    path('expenses/add/', ExpenseCreateView.as_view(), name='add_expense'),
    
    path('analytics/top-selling/', top_selling_dishes, name='top_selling_dishes'),
    path('analytics/daily-revenue/', daily_revenue, name='daily_revenue'),
    path('analytics/avg-order-value/', avg_order_value, name='avg_order_value'),
    path('analytics/order-type-dist/', order_type_distribution, name='order_type_distribution'),
    path('analytics/top-revenue-dishes/', top_revenue_dishes, name='top_revenue_dishes'),
]
