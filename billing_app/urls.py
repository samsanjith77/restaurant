from django.urls import path
from .views import *


urlpatterns = [
    # ==========================================
    # DISHES ENDPOINTS
    # ==========================================
    
    # List/Filter dishes - supports multiple query params:
    # ?meal_type=afternoon - filter by meal time (excludes extras)
    # ?category=extras - get ONLY extras
    # ?category=rice - filter by specific category (excludes extras)
    # ?group_by_category=true - grouped by category (excludes extras)
    # ?group_by_meal=true - grouped by meal type (excludes extras)
    # ?get_available_categories=true&meal_type=afternoon - get available categories
    path('dishes/', DishListView.as_view(), name='dish-list'),
    
    # Get single dish by ID
    path('dishes/<int:dish_id>/', DishDetailView.as_view(), name='dish-detail'),
    
    # Create new dish
    path('dishes/create/', CreateDishView.as_view(), name='create-dish'),
    
    # Update dish (full update)
    path('dishes/<int:dish_id>/update/', UpdateDishView.as_view(), name='update-dish'),
    
    # Delete dish (soft delete)
    path('dishes/<int:dish_id>/delete/', DeleteDishView.as_view(), name='delete-dish'),
    
    # Update dish price only
    path('dishes/<int:dish_id>/update-price/', UpdateDishPriceView.as_view(), name='update-dish-price'),
    
    # Update dish image only
    path('dishes/<int:dish_id>/update-image/', UpdateDishImageView.as_view(), name='update-dish-image'),
    
    # Get dishes for ordering page (grouped by meal_type and category)
    # Returns nested structure: meal_types -> categories -> dishes
    # Excludes 'extras' category and 'all' meal type
    path('dishes/for-ordering/', GetDishesForOrderingView.as_view(), name='dishes-for-ordering'),
    
    # Reorder dishes within a meal type and category
    # POST body: { "meal_type": "afternoon", "category": "rice", "dishes": [{dish_id, order}, ...] }
    path('dishes/reorder/', DishReorderView.as_view(), name='dish-reorder'),
    
    # Initialize display orders for existing dishes (run once)
    # Creates DishDisplayOrder entries for all dishes grouped by meal_type and category
    path('dishes/initialize-orders/', InitializeDishOrdersView.as_view(), name='initialize-orders'),
    
    # Get dish categories
    # ?meal_type=afternoon - categories for specific meal
    # ?include_extras=true - include extras in results
    path('dishes/categories/', DishCategoriesView.as_view(), name='dish-categories'),
    
    
    # ==========================================
    # ORDERS ENDPOINTS
    # ==========================================
    
    # Create new order
    path('orders/create/', CreateOrderView.as_view(), name='create-order'),
    
    # Get order history (with date range filter)
    path('orders/history/', OrderHistoryView.as_view(), name='order-history'),
    
    # Get single order details
    path('orders/<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    
    
    # ==========================================
    # PERSONS & EXPENSES ENDPOINTS
    # ==========================================
    
    # Worker endpoints
    path('workers/', WorkerListView.as_view(), name='workers'),
    path('workers/add/', WorkerCreateView.as_view(), name='add_worker'),
    
    # Material endpoints
    path('materials/', MaterialListView.as_view(), name='materials'),
    path('materials/add/', MaterialCreateView.as_view(), name='add_material'),
    
    # Expense endpoints
    path('expenses/filter/', ExpenseFilterView.as_view(), name='expenses_filter'),
    path('expenses/worker/add/', AddWorkerExpenseView.as_view(), name='add_worker_expense'),
    path('expenses/material/add/', AddMaterialExpenseView.as_view(), name='add_material_expense'),



    # ==========================================
    # ANALYTICS ENDPOINTS (AUTHENTICATED)
    # ==========================================

    # Main dashboard (shift-wise with top dishes)
    path('analytics/dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),

    # Category performance analysis
    path('analytics/categories/', CategoryPerformanceView.as_view(), name='analytics-categories'),

    # Hour-by-hour trends
    path('analytics/hourly/', HourlyTrendsView.as_view(), name='analytics-hourly'),

    # Day-to-day comparison
    path('analytics/comparison/', ComparisonView.as_view(), name='analytics-comparison'),

    # Low performing dishes
    path('analytics/low-performing/', LowPerformingDishesView.as_view(), name='analytics-low-performing'),

    # Worker expense breakdown
    path('analytics/worker-expenses/', WorkerExpenseBreakdownView.as_view(), name='analytics-worker-expenses'),

    # Material expense breakdown
    path('analytics/material-expenses/', MaterialExpenseBreakdownView.as_view(), name='analytics-material-expenses'),

    # Weekly summary report
    path('analytics/weekly-summary/', WeeklySummaryView.as_view(), name='analytics-weekly-summary'),
]
