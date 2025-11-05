from django.db import models
from django.utils import timezone

# ==========================================
# DISH MODEL - WITH MEAL TYPE SUPPORT
# ==========================================

class Dish(models.Model):
    MEAL_TYPE_CHOICES = [
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('night', 'Night'),
    ]
    
    name = models.CharField(max_length=100)
    secondary_name = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='dishes/', blank=True, null=True)
    meal_type = models.CharField(
        max_length=20,
        choices=MEAL_TYPE_CHOICES,
        default='afternoon'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-meal_type', 'name']
        indexes = [
            models.Index(fields=['meal_type', 'name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_meal_type_display()})"

    @property
    def meal_type_display(self):
        return self.get_meal_type_display()


# ==========================================
# ORDER MODEL - UNCHANGED
# ==========================================

class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('dine_in', 'Dine In'),
        ('delivery', 'Delivery'),
    ]

    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default='dine_in'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.get_order_type_display()}"


# ==========================================
# ORDER ITEM MODEL - UNCHANGED
# ==========================================

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.dish.name}"


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
