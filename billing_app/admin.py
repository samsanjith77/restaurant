# billing/admin.py
from django.contrib import admin
from .models import Dish, Order, OrderItem

@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'image')

admin.site.register(Order)
admin.site.register(OrderItem)