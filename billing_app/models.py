from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone


from django.core.validators import MinValueValidator
from decimal import Decimal

class Dish(models.Model):
    # Meal Time Choices (when to serve)
    MEAL_TYPE_CHOICES = [
        ('all', 'All Day'),
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('night', 'Night'),
    ]
    
    # Category choices for restaurant page display
    CATEGORY_CHOICES = [
        ('rice', 'Rice'),
        ('gravy', 'Gravy'),
        ('curry', 'Curry'),
        ('sidedish', 'Side Dish'),
        ('dosa', 'Dosa'),
        ('porotta', 'Porotta'),
        ('chinese', 'Chinese'),
        ('extras', 'Extras'),
    ]
    
    # Define which categories are available during which meal times
    # Categories not in this dict are available at all times
    CATEGORY_MEAL_RESTRICTIONS = {
        'dosa': ['morning', 'night'],      # Dosa only for morning and night
        'porotta': ['afternoon','night'],              # Porotta only for night
        'chinese': ['afternoon', 'night'], # Chinese for afternoon and night
        # extras category has no restrictions - available at all times
        # Add more restrictions as needed
    }
    
    name = models.CharField(max_length=200)
    secondary_name = models.CharField(max_length=200, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    meal_type = models.CharField(
        max_length=20, 
        choices=MEAL_TYPE_CHOICES, 
        default='afternoon'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='rice'
    )
    image = models.ImageField(upload_to='dishes/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Dishes"
        ordering = ['category', 'name']
    
    def __str__(self):
        category_display = self.get_category_display()
        return f"{self.name} ({category_display}) - {self.get_meal_type_display()}"
    
    def clean(self):
        """
        Validate that the dish's meal_type is compatible with its category restrictions
        """
        super().clean()
        
        # Skip validation if category is not set
        if not self.category:
            return
        
        # Extras category bypasses all meal restrictions
        if self.category == 'extras':
            return
        
        # Check if this category has meal restrictions
        if self.category in self.CATEGORY_MEAL_RESTRICTIONS:
            allowed_meal_types = self.CATEGORY_MEAL_RESTRICTIONS[self.category]
            
            # 'all' meal type bypasses restrictions
            if self.meal_type != 'all' and self.meal_type not in allowed_meal_types:
                allowed_display = ', '.join([
                    dict(self.MEAL_TYPE_CHOICES).get(mt, mt) 
                    for mt in allowed_meal_types
                ])
                raise ValidationError({
                    'meal_type': f"{self.get_category_display()} items can only be served during: {allowed_display}. "
                                f"Current selection: {self.get_meal_type_display()}"
                })
    
    def save(self, *args, **kwargs):
        """Override save to call full_clean for validation"""
        # Only validate if not skipping validation (useful for bulk operations)
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_available_categories_for_meal(cls, meal_type):
        """
        Return list of categories available for a specific meal type
        """
        if meal_type == 'all':
            # Return all categories when 'all' is selected
            return [cat[0] for cat in cls.CATEGORY_CHOICES]
        
        available_categories = []
        for category_code, category_name in cls.CATEGORY_CHOICES:
            # Extras are always available
            if category_code == 'extras':
                available_categories.append(category_code)
                continue
            
            if category_code in cls.CATEGORY_MEAL_RESTRICTIONS:
                # Check if meal_type is in the allowed list
                if meal_type in cls.CATEGORY_MEAL_RESTRICTIONS[category_code]:
                    available_categories.append(category_code)
            else:
                # Category has no restrictions, available for all meals
                available_categories.append(category_code)
        
        return available_categories
    
    @classmethod
    def is_category_available_for_meal(cls, category, meal_type):
        """
        Check if a specific category is available for a meal type
        """
        if meal_type == 'all' or category == 'extras':
            return True
        
        if category in cls.CATEGORY_MEAL_RESTRICTIONS:
            return meal_type in cls.CATEGORY_MEAL_RESTRICTIONS[category]
        
        return True  # No restrictions means available


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
    
    def get_subtotal(self):
        """Calculate subtotal for this order item"""
        return self.price * self.quantity


class DishDisplayOrder(models.Model):
    """
    Table to store display order of dishes within each meal time and category
    Order starts from 0 for each meal_type + category combination separately
    Excludes 'extras' category from ordering
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
    category = models.CharField(
        max_length=20,
        choices=Dish.CATEGORY_CHOICES
    )
    order = models.IntegerField(default=0)  # Order within meal_type + category (starts from 0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['meal_type', 'category', 'order']
        verbose_name = "Dish Display Order"
        verbose_name_plural = "Dish Display Orders"
        # Unique constraint: same order number can't exist for same meal_type + category
        unique_together = [['meal_type', 'category', 'order']]
        indexes = [
            models.Index(fields=['meal_type', 'category', 'order']),
            models.Index(fields=['meal_type', 'order']),
        ]
    
    def __str__(self):
        return f"{self.dish.name} - {self.get_meal_type_display()} - {self.get_category_display()} - Order: {self.order}"
    
    def clean(self):
        """
        Validate that extras category is not being ordered
        """
        super().clean()
        
        if self.category == 'extras':
            raise ValidationError({
                'category': "Extras category cannot be ordered. They are always available."
            })
        
        # Ensure dish's category matches the order's category
        if self.dish and self.dish.category != self.category:
            raise ValidationError({
                'category': f"Category mismatch. Dish category is '{self.dish.get_category_display()}' "
                           f"but order category is '{self.get_category_display()}'"
            })
        
        # Ensure dish's meal_type matches the order's meal_type
        if self.dish and self.dish.meal_type != self.meal_type:
            raise ValidationError({
                'meal_type': f"Meal type mismatch. Dish meal type is '{self.dish.get_meal_type_display()}' "
                            f"but order meal type is '{self.get_meal_type_display()}'"
            })
    
    def save(self, *args, **kwargs):
        """
        Auto-assign order if not set
        Sync category and meal_type from dish
        """
        # Sync category and meal_type from dish
        if self.dish:
            self.category = self.dish.category
            self.meal_type = self.dish.meal_type
        
        # Validate before saving
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        
        # Auto-assign order if not set (for new records)
        if self.order == 0 and not self.pk:
            # Get the max order for this meal type + category combination
            max_order = DishDisplayOrder.objects.filter(
                meal_type=self.meal_type,
                category=self.category
            ).aggregate(models.Max('order'))['order__max']
            
            self.order = (max_order or -1) + 1
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_next_order(cls, meal_type, category):
        """
        Get the next available order number for a meal_type + category combination
        """
        max_order = cls.objects.filter(
            meal_type=meal_type,
            category=category
        ).aggregate(models.Max('order'))['order__max']
        
        return (max_order or -1) + 1
    
    @classmethod
    def reorder_category(cls, meal_type, category, dishes_order_list):
        """
        Reorder dishes within a specific meal_type + category
        
        dishes_order_list: List of tuples [(dish_id, new_order), ...]
        """
        from django.db import transaction
        
        with transaction.atomic():
            for dish_id, new_order in dishes_order_list:
                cls.objects.filter(
                    dish_id=dish_id,
                    meal_type=meal_type,
                    category=category
                ).update(order=new_order)



class Worker(models.Model):
    """Renamed from Person - Track workers/employees"""
    ROLE_CHOICES = [
        ('worker', 'Worker / Operator'),
        ('manager', 'Manager'),
        ('supervisor', 'Supervisor'),
    ]

    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    contact = models.CharField(max_length=20, blank=True, null=True)
    joined_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Workers"

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"


class Material(models.Model):
    """Track different types of materials"""
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('bag', 'Bag'),
        ('ton', 'Ton'),
        ('piece', 'Piece'),
        ('meter', 'Meter'),
        ('liter', 'Liter'),
        ('box', 'Box'),
        ('bundle', 'Bundle'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Materials"

    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"


class Expense(models.Model):
    """Main expense record - supports both worker and material expenses"""
    EXPENSE_TYPE_CHOICES = [
        ('worker', 'Worker Expense'),
        ('material', 'Material Expense'),
    ]

    WORKER_CATEGORY_CHOICES = [
        ('wage', 'Daily Wage'),
        ('bonus', 'Bonus'),
        ('transport', 'Transport'),
        ('food', 'Food'),
        ('advance', 'Advance Payment'),
        ('other', 'Other'),
    ]

    expense_type = models.CharField(
        max_length=20,
        choices=EXPENSE_TYPE_CHOICES,
        default='worker'
    )
    
    # For worker expenses
    worker = models.ForeignKey(
        Worker,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    worker_category = models.CharField(
        max_length=50,
        choices=WORKER_CATEGORY_CHOICES,
        blank=True,
        null=True
    )
    
    description = models.CharField(max_length=255)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Expenses"

    def __str__(self):
        if self.expense_type == 'worker' and self.worker:
            return f"Worker: {self.worker.name} - ₹{self.total_amount}"
        else:
            return f"Material: {self.description} - ₹{self.total_amount}"

    def save(self, *args, **kwargs):
        # Calculate total_amount for material expenses from items
        if self.expense_type == 'material' and self.pk:
            items_total = self.items.aggregate(
                total=models.Sum('subtotal')
            )['total'] or Decimal('0.00')
            self.total_amount = items_total
        super().save(*args, **kwargs)


class ExpenseItem(models.Model):
    """Individual material items in a material expense"""
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name='items'
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='expense_items'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False
    )

    class Meta:
        ordering = ['id']
        verbose_name_plural = "Expense Items"

    def __str__(self):
        return f"{self.material.name} x {self.quantity} @ ₹{self.unit_price}"

    def save(self, *args, **kwargs):
        # Auto-calculate subtotal
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
        # Update parent expense total
        if self.expense_id:
            self.expense.save()