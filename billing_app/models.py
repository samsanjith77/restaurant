from django.db import models
from django.contrib.auth.models import User
# from datetime import datetime,timezone

from django.utils import timezone
class Dish(models.Model):
    # Meal Time Choices (when to serve)
    MEAL_TYPE_CHOICES = [
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('night', 'Night'),
    ]
    
    # Dish Category/Type Choices (what kind of dish)
    DISH_TYPE_CHOICES = [
        ('meals', 'Meals'),
        ('chinese', 'Chinese'),
        ('indian', 'Indian'),
        ('addons', 'Add-ons'),
        ('beverages', 'Beverages'),
        ('desserts', 'Desserts'),
    ]
    
    name = models.CharField(max_length=200)
    secondary_name = models.CharField(max_length=200, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    meal_type = models.CharField(
        max_length=20, 
        choices=MEAL_TYPE_CHOICES, 
        default='afternoon'
    )
    dish_type = models.CharField(
        max_length=20,
        choices=DISH_TYPE_CHOICES,
        default='meals'
    )
    image = models.ImageField(upload_to='dishes/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Dishes"
        ordering = ['dish_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_dish_type_display()}) - {self.get_meal_type_display()}"


class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('dine-in', 'Dine In'),
        ('delivery', 'Delivery'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('card', 'Card'),
    ]
    
    order_type = models.CharField(
        max_length=20, 
        choices=ORDER_TYPE_CHOICES, 
        default='dine-in'
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='cash'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    addons = models.JSONField(null=True, blank=True, default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.get_order_type_display()} - ₹{self.total_amount}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.dish.name} x {self.quantity}"


# ==========================================
# PERSON MODEL - UNCHANGED
# ==========================================

class Person(models.Model):
    ROLE_CHOICES = [
        ('worker', 'Worker / Operator'),
        ('manager', 'Manager'),
    ]

    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    contact = models.CharField(max_length=20, blank=True, null=True)
    joined_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"


# ==========================================
# EXPENSE MODEL - UNCHANGED
# ==========================================

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('wage', 'Worker Wage'),
        ('material', 'Material Purchase'),
        ('maintenance', 'Maintenance'),
        ('food', 'Food / Canteen'),
        ('other', 'Other'),
    ]

    person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other'
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        person_name = self.person.name if self.person else "N/A"
        return f"{self.category} - {person_name} - ₹{self.amount}"


class DishDisplayOrder(models.Model):
    """
    Table to store display order of dishes within each meal time
    Order starts from 0 for each meal_type separately
    """
    dish = models.OneToOneField(
        Dish, 
        on_delete=models.CASCADE, 
        related_name='display_order_info',
        unique=True
    )
    meal_type = models.CharField(
        max_length=20,
        choices=Dish.MEAL_TYPE_CHOICES
    )
    order = models.IntegerField(default=0)  # Order within meal_type (starts from 0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['meal_type', 'order']
        verbose_name = "Dish Display Order"
        verbose_name_plural = "Dish Display Orders"
        # REMOVE the unique constraint - it causes issues during updates
        indexes = [
            models.Index(fields=['meal_type', 'order']),
        ]
    
    def __str__(self):
        return f"{self.dish.name} - {self.meal_type} - Order: {self.order}"
