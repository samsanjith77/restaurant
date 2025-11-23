from django.urls import path

from .views import *
urlpatterns = [
    # Dishes
    path('dishes/', DishListView.as_view(), name='dish-list'),
    path('dishes/types/', DishTypesView.as_view(), name='dish-types'),
    path('dishes/<int:dish_id>/', DishDetailView.as_view(), name='dish-detail'),
    path('dishes/create/', CreateDishView.as_view(), name='create-dish'),
    path('dishes/<int:dish_id>/delete/', DeleteDishView.as_view(), name='delete-dish'),
    path('dishes/<int:dish_id>/update-price/', UpdateDishPriceView.as_view(), name='update-dish-price'),
    path('dishes/<int:dish_id>/update-image/', UpdateDishImageView.as_view(), name='update-dish-image'),
    
    # Orders
    path('orders/create/', CreateOrderView.as_view(), name='create-order'),
    path('orders/history/', OrderHistoryView.as_view(), name='last-orders'),
    # expenditure
    path('persons/', PersonListView.as_view(), name='persons'),
    path('expenses/filter/', ExpenseFilterView.as_view(), name='expenses_filter'),
    path('persons/add/', PersonCreateView.as_view(), name='add_person'),
    path('expenses/add/', ExpenseCreateView.as_view(), name='add_expense'),

    path('analytics/summary/', AnalyticsSummaryView.as_view(), name='analytics_summary'),
    path('analytics/worker-expense/', WorkerExpenseByDateView.as_view(), name='worker_expense_by_date'),
    path('analytics/daily-revenue-trend/', DailyRevenueTrendView.as_view(), name='daily-revenue-trend'),
    path('analytics/top-selling-dishes/', TopSellingDishesView.as_view(), name='top-selling-dishes'),
]
