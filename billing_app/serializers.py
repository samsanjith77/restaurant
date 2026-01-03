from rest_framework import serializers
from .models import Order, OrderItem, Expense, ExpenseItem, Dish, Worker, Material
from decimal import Decimal

class ShiftReportSerializer(serializers.Serializer):
    """Serializer for shift-wise report data"""
    shift_type = serializers.CharField()
    shift_start = serializers.DateTimeField()
    shift_end = serializers.DateTimeField()
    
    # Income section
    total_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    dine_in_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    delivery_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_count = serializers.IntegerField()
    
    # Income breakdown by payment type
    cash_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    upi_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    card_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Top selling dishes
    top_dishes = serializers.ListField(child=serializers.DictField())
    
    # Expense section
    total_expense = serializers.DecimalField(max_digits=10, decimal_places=2)
    worker_expense = serializers.DecimalField(max_digits=10, decimal_places=2)
    material_expense = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Worker expense breakdown
    worker_expenses_detail = serializers.ListField(child=serializers.DictField())
    
    # Material expense breakdown
    material_expenses_detail = serializers.ListField(child=serializers.DictField())
    
    # Profit calculation
    profit = serializers.DecimalField(max_digits=10, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)


class DailyReportSerializer(serializers.Serializer):
    """Serializer for full day report with all shifts"""
    date = serializers.DateField()
    shifts = ShiftReportSerializer(many=True)
    
    # Daily totals
    daily_total_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    daily_total_expense = serializers.DecimalField(max_digits=10, decimal_places=2)
    daily_profit = serializers.DecimalField(max_digits=10, decimal_places=2)
