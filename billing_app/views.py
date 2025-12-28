from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

from django.db.models import F, Sum, DecimalField, Count, Q, Max
from .models import *
import json
from django.utils.dateparse import parse_datetime, parse_date
from .print_utils import print_order_bill 
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import date, datetime, timedelta
from rest_framework.views import APIView
from decimal import Decimal
from django.db import transaction
import json
from django.http import JsonResponse
from django.views import View
from django.db.models import Sum, Count, F, Q, DecimalField, Avg
from django.db.models.functions import Coalesce, TruncHour, TruncDate
from datetime import datetime, time, timedelta
from decimal import Decimal
from collections import defaultdict
from .models import Order, OrderItem, Dish, Expense, Worker, Material, ExpenseItem
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
# ==========================================
# DISH LIST VIEW - WITH EXTRAS ISOLATION
# ==========================================
class DishListView(View):
    def get(self, request):
        try:
            # Get filter parameters
            meal_type = request.GET.get('meal_type', None)
            category = request.GET.get('category', None)
            group_by_meal = request.GET.get('group_by_meal', 'false').lower() == 'true'
            group_by_category = request.GET.get('group_by_category', 'false').lower() == 'true'
            get_available_categories = request.GET.get('get_available_categories', 'false').lower() == 'true'
            
            # Return available categories for a meal type
            if get_available_categories:
                if not meal_type:
                    return JsonResponse({
                        "error": "meal_type parameter is required when get_available_categories=true"
                    }, status=400)
                
                # Get available categories excluding extras
                available_categories = Dish.get_available_categories_for_meal(meal_type)
                available_categories = [cat for cat in available_categories if cat != 'extras']
                
                category_data = [
                    {
                        'code': cat_code,
                        'display': cat_display
                    }
                    for cat_code, cat_display in Dish.CATEGORY_CHOICES
                    if cat_code in available_categories
                ]
                return JsonResponse(category_data, safe=False)
            
            # If group_by_category=true, return grouped by category (EXCLUDES EXTRAS)
            if group_by_category:
                return self.get_grouped_by_category(request, meal_type)
            
            # If group_by_meal=true, return grouped data for ordering page
            if group_by_meal:
                return self.get_grouped_by_meal_type(request)
            
            # Start with all active dishes
            dishes = Dish.objects.filter(is_active=True)
            
            # CRITICAL: If category is explicitly 'extras', show only extras
            if category == 'extras':
                dishes = dishes.filter(category='extras')
            else:
                # For all other queries, EXCLUDE extras by default
                dishes = dishes.exclude(category='extras')
                
                # Filter by specific category if provided (and it's not extras)
                if category:
                    valid_categories = [choice[0] for choice in Dish.CATEGORY_CHOICES]
                    if category not in valid_categories:
                        return JsonResponse({
                            "error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"
                        }, status=400)
                    dishes = dishes.filter(category=category)
            
            # Filter by meal_type if provided (doesn't apply to extras)
            if meal_type and category != 'extras':
                valid_meal_types = [choice[0] for choice in Dish.MEAL_TYPE_CHOICES]
                if meal_type not in valid_meal_types:
                    return JsonResponse({
                        "error": f"Invalid meal_type. Must be one of: {', '.join(valid_meal_types)}"
                        }, status=400)
                
                # Handle 'all' meal type
                if meal_type == 'all':
                    pass  # Don't filter by meal_type
                else:
                    # Show dishes for specific meal_type OR dishes marked as 'all'
                    dishes = dishes.filter(Q(meal_type=meal_type) | Q(meal_type='all'))
            
            # Order results - UNIFIED ORDERING LOGIC
            if meal_type and meal_type != 'all' and category != 'extras':
                # Use select_related for efficient ordering
                dishes = dishes.select_related('display_order_info').order_by(
                    'category',
                    'display_order_info__order',
                    'id'  # Add id as tiebreaker for consistent ordering
                )
            else:
                dishes = dishes.order_by('category', 'name')
            
            # Build response data
            data = []
            for dish in dishes:
                dish_data = {
                    'id': dish.id,
                    'name': dish.name,
                    'secondary_name': dish.secondary_name,
                    'price': float(dish.price),
                    'meal_type': dish.meal_type,
                    'meal_type_display': dish.get_meal_type_display(),
                    'category': dish.category,
                    'category_display': dish.get_category_display(),
                    'image': request.build_absolute_uri(dish.image.url) if dish.image else None,
                    'is_active': dish.is_active,
                    'created_at': dish.created_at.isoformat(),
                }
                
                if meal_type and meal_type != 'all' and category != 'extras':
                    try:
                        dish_data['order'] = dish.display_order_info.order
                    except DishDisplayOrder.DoesNotExist:
                        dish_data['order'] = 0  # Default to 0 for consistency
                
                data.append(dish_data)
            
            return JsonResponse(data, safe=False)
        
        except Exception as e:
            import traceback
            print("Error in DishListView:")
            print(traceback.format_exc())
            return JsonResponse({
                "error": str(e)
            }, status=500)
    
    def get_grouped_by_category(self, request, meal_type=None):
        """
        Get dishes grouped by category for restaurant page
        Called when ?group_by_category=true
        ALWAYS EXCLUDES 'extras' category
        """
        try:
            categories_data = []
            
            # Base queryset - ALWAYS exclude extras category
            base_query = Dish.objects.filter(is_active=True).exclude(category='extras')
            
            # Handle meal_type filtering
            if meal_type:
                if meal_type == 'all':
                    pass  # Show all dishes
                else:
                    # Show dishes for specific meal_type OR dishes marked as 'all'
                    base_query = base_query.filter(Q(meal_type=meal_type) | Q(meal_type='all'))
            
            # Get available categories for this meal type (excluding extras)
            if meal_type and meal_type != 'all':
                available_categories = Dish.get_available_categories_for_meal(meal_type)
            else:
                available_categories = [cat[0] for cat in Dish.CATEGORY_CHOICES]
            
            # Remove extras from available categories
            available_categories = [cat for cat in available_categories if cat != 'extras']
            
            # Only iterate through available categories (excluding extras)
            for category_code, category_name in Dish.CATEGORY_CHOICES:
                # Skip extras category completely
                if category_code == 'extras':
                    continue
                
                # Skip categories not available for this meal time
                if category_code not in available_categories:
                    continue
                
                # Get dishes for this category - UNIFIED ORDERING
                dishes = base_query.filter(category=category_code).select_related(
                    'display_order_info'
                ).order_by(
                    'display_order_info__order',
                    'id'  # Add id as tiebreaker
                )
                
                dishes_data = []
                for dish in dishes:
                    try:
                        order = dish.display_order_info.order
                    except DishDisplayOrder.DoesNotExist:
                        order = 0  # Default to 0
                    
                    dishes_data.append({
                        'id': dish.id,
                        'name': dish.name,
                        'secondary_name': dish.secondary_name,
                        'price': float(dish.price),
                        'meal_type': dish.meal_type,
                        'meal_type_display': dish.get_meal_type_display(),
                        'order': order,
                        'image': request.build_absolute_uri(dish.image.url) if dish.image else None
                    })
                
                # Only add category if it has dishes
                if dishes_data:
                    categories_data.append({
                        'category': category_code,
                        'category_display': category_name,
                        'dishes': dishes_data,
                        'total_dishes': len(dishes_data)
                    })
            
            return JsonResponse(categories_data, safe=False)
        
        except Exception as e:
            import traceback
            print("Error in get_grouped_by_category:")
            print(traceback.format_exc())
            return JsonResponse({
                "error": str(e)
            }, status=500)
    
    def get_grouped_by_meal_type(self, request):
        """
        Get all dishes grouped by meal_type for the ordering page UI
        Called when ?group_by_meal=true
        EXCLUDES extras from this view
        """
        try:
            meal_types_data = []
            
            for meal_code, meal_name in Dish.MEAL_TYPE_CHOICES:
                # Get dishes for this meal_type ordered by order field
                # EXCLUDE extras category - UNIFIED ORDERING
                dishes = Dish.objects.filter(
                    meal_type=meal_code,
                    is_active=True
                ).exclude(
                    category='extras'
                ).select_related('display_order_info').order_by(
                    'display_order_info__order',
                    'id'  # Add id as tiebreaker
                )
                
                dishes_data = []
                for dish in dishes:
                    try:
                        order = dish.display_order_info.order
                    except DishDisplayOrder.DoesNotExist:
                        order = 0  # Default to 0
                    
                    dishes_data.append({
                        'id': dish.id,
                        'name': dish.name,
                        'secondary_name': dish.secondary_name,
                        'price': float(dish.price),
                        'category': dish.category,
                        'category_display': dish.get_category_display(),
                        'order': order,
                        'image': request.build_absolute_uri(dish.image.url) if dish.image else None
                    })
                
                meal_types_data.append({
                    'meal_type': meal_code,
                    'meal_type_display': meal_name,
                    'dishes': dishes_data,
                    'total_dishes': len(dishes_data)
                })
            
            return JsonResponse(meal_types_data, safe=False)
        
        except Exception as e:
            import traceback
            print("Error in get_grouped_by_meal_type:")
            print(traceback.format_exc())
            return JsonResponse({
                "error": str(e)
            }, status=500)


# ==========================================
# GET DISHES FOR ORDERING (GROUPED BY MEAL TYPE AND CATEGORY)
# ==========================================
class GetDishesForOrderingView(View):
    """
    Returns dishes grouped by meal_type, then by category
    Excludes 'extras' category
    """
    def get(self, request):
        try:
            meal_types_data = []
            
            for meal_code, meal_name in Dish.MEAL_TYPE_CHOICES:
                # Skip 'all' meal type (used for extras only)
                if meal_code == 'all':
                    continue
                
                # Get categories for this meal type (exclude extras)
                categories = Dish.objects.filter(
                    meal_type=meal_code,
                    is_active=True  # FIXED: Changed from is_available to is_active
                ).exclude(
                    category='extras'
                ).values_list('category', flat=True).distinct().order_by('category')
                
                categories_data = []
                total_dishes_count = 0
                
                for category in categories:
                    # Get dishes for this category, ordered by display_order
                    dishes = Dish.objects.filter(
                        meal_type=meal_code,
                        category=category,
                        is_active=True  # FIXED: Changed from is_available to is_active
                    ).select_related('display_order_info').order_by(
                        'display_order_info__order', 'id'
                    )
                    
                    dishes_list = []
                    for dish in dishes:
                        # Get the current order or default to 0
                        try:
                            current_order = dish.display_order_info.order
                        except DishDisplayOrder.DoesNotExist:
                            current_order = 0
                        
                        dishes_list.append({
                            'id': dish.id,
                            'name': dish.name,
                            'secondary_name': dish.secondary_name,
                            'price': str(dish.price),
                            'image': dish.image.url if dish.image else None,
                            'category': dish.category,
                            'category_display': dish.get_category_display(),
                            'current_order': current_order
                        })
                    
                    if dishes_list:
                        categories_data.append({
                            'category': category,
                            'category_display': dict(Dish.CATEGORY_CHOICES).get(category, category),
                            'dishes': dishes_list,
                            'total_dishes': len(dishes_list)
                        })
                        total_dishes_count += len(dishes_list)
                
                if categories_data:
                    meal_types_data.append({
                        'meal_type': meal_code,
                        'meal_type_display': meal_name,
                        'categories': categories_data,
                        'total_dishes': total_dishes_count
                    })
            
            return JsonResponse(meal_types_data, safe=False)
        
        except Exception as e:
            import traceback
            print("Error in GetDishesForOrderingView:")
            print(traceback.format_exc())
            return JsonResponse({
                "error": str(e)
            }, status=500)


# ==========================================
# DISH REORDER VIEW (BY MEAL TYPE AND CATEGORY)
# ==========================================
# ==========================================
# DISH REORDER VIEW (BY MEAL TYPE AND CATEGORY)
# ==========================================
@method_decorator(csrf_exempt, name='dispatch')
class DishReorderView(View):
    def put(self, request):
        try:
            data = json.loads(request.body)
            meal_type = data.get('meal_type')
            category = data.get('category')
            dishes_order = data.get('dishes', [])
            
            # Validate meal_type
            valid_meal_types = [choice[0] for choice in Dish.MEAL_TYPE_CHOICES if choice[0] != 'all']
            if not meal_type or meal_type not in valid_meal_types:
                return JsonResponse({
                    "error": f"Invalid meal_type. Must be one of: {', '.join(valid_meal_types)}"
                }, status=400)
            
            # Validate category
            valid_categories = [choice[0] for choice in Dish.CATEGORY_CHOICES if choice[0] != 'extras']
            if not category or category not in valid_categories:
                return JsonResponse({
                    "error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"
                }, status=400)
            
            # Validate dishes array
            if not dishes_order or not isinstance(dishes_order, list):
                return JsonResponse({
                    "error": "dishes array is required"
                }, status=400)
            
            # Validate each dish item
            for item in dishes_order:
                if 'dish_id' not in item or 'order' not in item:
                    return JsonResponse({
                        "error": "Each dish must have 'dish_id' and 'order' keys"
                    }, status=400)
            
            # Update orders in transaction
            with transaction.atomic():
                dish_ids = [item['dish_id'] for item in dishes_order]
                
                # Verify all dishes exist, belong to the meal_type and category
                dishes_in_db = Dish.objects.filter(
                    id__in=dish_ids,
                    meal_type=meal_type,
                    category=category,
                    is_active=True
                ).exclude(category='extras').count()
                
                if dishes_in_db != len(dish_ids):
                    return JsonResponse({
                        "error": "Some dishes not found or don't belong to this meal_type/category"
                    }, status=400)
                
                # STEP 1: Set all orders to negative values temporarily to avoid unique constraint conflicts
                for item in dishes_order:
                    DishDisplayOrder.objects.filter(
                        dish_id=item['dish_id']
                    ).update(order=-item['order'] - 1000)
                
                # STEP 2: Now set the actual order values
                for item in dishes_order:
                    DishDisplayOrder.objects.update_or_create(
                        dish_id=item['dish_id'],
                        defaults={
                            'meal_type': meal_type,
                            'category': category,
                            'order': item['order']
                        }
                    )
            
            return JsonResponse({
                "success": True,
                "message": f"Successfully reordered {len(dishes_order)} dishes for {category} in {meal_type}",
                "meal_type": meal_type,
                "category": category,
                "updated_count": len(dishes_order)
            })
        
        except json.JSONDecodeError:
            return JsonResponse({
                "error": "Invalid JSON payload"
            }, status=400)
        except Exception as e:
            import traceback
            print("Error in DishReorderView:")
            print(traceback.format_exc())
            return JsonResponse({
                "error": str(e)
            }, status=500)



# ==========================================
# INITIALIZE DISH ORDERS VIEW
# ==========================================
@method_decorator(csrf_exempt, name='dispatch')
class InitializeDishOrdersView(View):
    """
    Initialize display orders for existing dishes (run once)
    EXCLUDES extras category
    Groups by meal_type and category
    """
    def post(self, request):
        try:
            created_count = 0
            updated_count = 0
            
            # For each meal_type
            for meal_code, meal_name in Dish.MEAL_TYPE_CHOICES:
                if meal_code == 'all':  # Skip 'all' (for extras)
                    continue
                
                # For each category (exclude extras)
                for cat_code, cat_name in Dish.CATEGORY_CHOICES:
                    if cat_code == 'extras':
                        continue
                    
                    # Get dishes for this meal_type and category
                    dishes = Dish.objects.filter(
                        meal_type=meal_code,
                        category=cat_code,
                        is_active=True  # FIXED: Changed from is_available to is_active
                    ).order_by('id')
                    
                    for index, dish in enumerate(dishes):
                        obj, created = DishDisplayOrder.objects.update_or_create(
                            dish=dish,
                            defaults={
                                'meal_type': meal_code,
                                'category': cat_code,
                                'order': index
                            }
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
            
            return JsonResponse({
                "success": True,
                "message": f"Initialized dish orders",
                "created": created_count,
                "updated": updated_count,
                "details": "Orders grouped by meal_type and category (extras excluded)"
            })
        
        except Exception as e:
            import traceback
            print("Error in InitializeDishOrdersView:")
            print(traceback.format_exc())
            return JsonResponse({
                "error": str(e)
            }, status=500)


# ==========================================
# GET DISH CATEGORIES
# ==========================================
class DishCategoriesView(View):
    def get(self, request):
        try:
            meal_type = request.GET.get('meal_type', None)
            include_extras = request.GET.get('include_extras', 'false').lower() == 'true'
            
            if meal_type:
                # Return categories available for specific meal type
                available_categories = Dish.get_available_categories_for_meal(meal_type)
                categories = [
                    {
                        'value': choice[0],
                        'label': choice[1]
                    }
                    for choice in Dish.CATEGORY_CHOICES
                    if choice[0] in available_categories
                ]
            else:
                # Return all categories
                categories = [
                    {
                        'value': choice[0],
                        'label': choice[1]
                    }
                    for choice in Dish.CATEGORY_CHOICES
                ]
            
            # EXCLUDE extras unless explicitly requested
            if not include_extras:
                categories = [cat for cat in categories if cat['value'] != 'extras']
            
            return JsonResponse(categories, safe=False)
        except Exception as e:
            import traceback
            print("Error in DishCategoriesView:")
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)
# ==========================================
# GET SINGLE DISH BY ID
# ==========================================
class DishDetailView(View):
    def get(self, request, dish_id):
        try:
            dish = Dish.objects.get(id=dish_id)
            data = {
                "id": dish.id,
                "name": dish.name,
                "secondary_name": dish.secondary_name,
                "price": float(dish.price),
                "meal_type": dish.meal_type,
                "meal_type_display": dish.get_meal_type_display(),
                "category": dish.category,
                "category_display": dish.get_category_display(),
                "image": request.build_absolute_uri(dish.image.url) if dish.image else None,
                "is_active": dish.is_active,
                "created_at": dish.created_at.isoformat(),
                "updated_at": dish.updated_at.isoformat(),
            }
            return JsonResponse(data)
        
        except Dish.DoesNotExist:
            return JsonResponse({
                "error": "Dish not found"
            }, status=404)
        
        except Exception as e:
            return JsonResponse({
                "error": str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CreateDishView(View):
    def post(self, request):
        try:
            name = request.POST.get('name', '').strip()
            secondary_name = request.POST.get('secondary_name', '').strip()
            price = request.POST.get('price', '').strip()
            meal_type = request.POST.get('meal_type', 'afternoon').strip()
            category = request.POST.get('category', 'rice').strip()
            image = request.FILES.get('image')
            
            # Validation - required fields
            if not name:
                return JsonResponse({"error": "Dish name is required"}, status=400)
            
            if not price:
                return JsonResponse({"error": "Price is required"}, status=400)
            
            # Validate price
            try:
                price_float = float(price)
                if price_float < 0:
                    raise ValueError("Price cannot be negative")
            except ValueError:
                return JsonResponse({
                    "error": "Price must be a valid positive number"
                }, status=400)
            
            # Validate meal_type
            valid_meal_types = [choice[0] for choice in Dish.MEAL_TYPE_CHOICES]
            if meal_type not in valid_meal_types:
                return JsonResponse({
                    "error": f"Invalid meal_type. Must be one of: {', '.join(valid_meal_types)}"
                }, status=400)
            
            # Validate category
            valid_categories = [choice[0] for choice in Dish.CATEGORY_CHOICES]
            if category not in valid_categories:
                return JsonResponse({
                    "error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"
                }, status=400)
            
            # Check if category is allowed for this meal type (skip for extras)
            if category != 'extras' and hasattr(Dish, 'is_category_available_for_meal'):
                if not Dish.is_category_available_for_meal(category, meal_type):
                    return JsonResponse({
                        "error": f"Category '{category}' is not available for meal type '{meal_type}'"
                    }, status=400)
            
            # Use transaction to ensure atomicity
            with transaction.atomic():
                # Create dish
                dish = Dish.objects.create(
                    name=name,
                    secondary_name=secondary_name if secondary_name else None,
                    price=price_float,
                    meal_type=meal_type,
                    category=category,
                    image=image
                )
                
                # Determine which meal types need display orders
                meal_types_to_order = []
                
                if category == 'extras':
                    # Extras don't need display orders (available at all times)
                    pass
                elif meal_type == 'all':
                    # If meal_type is 'all', create orders for morning, afternoon, and night
                    meal_types_to_order = ['morning', 'afternoon', 'night']
                else:
                    # Normal case - just the selected meal type
                    meal_types_to_order = [meal_type]
                
                # Create display order entries
                for mt in meal_types_to_order:
                    try:
                        # Get the next available order for this meal type
                        max_order_result = DishDisplayOrder.objects.filter(
                            meal_type=mt
                        ).aggregate(Max('order'))
                        
                        max_order = max_order_result['order__max']
                        next_order = (max_order if max_order is not None else -1) + 1
                        
                        # Check if this dish already has a display order for this meal type
                        existing_order = DishDisplayOrder.objects.filter(
                            dish=dish,
                            meal_type=mt
                        ).first()
                        
                        if existing_order:
                            # Update existing order
                            existing_order.order = next_order
                            existing_order.save()
                            print(f"✅ Updated display order for {dish.name} - {mt}: {next_order}")
                        else:
                            # Create new display order
                            DishDisplayOrder.objects.create(
                                dish=dish,
                                meal_type=mt,
                                order=next_order
                            )
                            print(f"✅ Created display order for {dish.name} - {mt}: {next_order}")
                    
                    except Exception as order_error:
                        # Log the error but don't fail the dish creation
                        print(f"⚠️ Display order creation warning for {mt}: {str(order_error)}")
                        # If it's a unique constraint error, try to find and use the next available order
                        if 'unique constraint' in str(order_error).lower():
                            try:
                                # Find the actual maximum order including any gaps
                                all_orders = DishDisplayOrder.objects.filter(
                                    meal_type=mt
                                ).values_list('order', flat=True).order_by('order')
                                
                                # Find next available order (handling gaps)
                                used_orders = set(all_orders)
                                next_order = 0
                                while next_order in used_orders:
                                    next_order += 1
                                
                                DishDisplayOrder.objects.create(
                                    dish=dish,
                                    meal_type=mt,
                                    order=next_order
                                )
                                print(f"✅ Created display order (gap-filled) for {dish.name} - {mt}: {next_order}")
                            except Exception as retry_error:
                                print(f"❌ Failed to create display order after retry: {str(retry_error)}")
            
            return JsonResponse({
                "message": "Dish created successfully!",
                "dish": {
                    "id": dish.id,
                    "name": dish.name,
                    "secondary_name": dish.secondary_name or "",
                    "price": float(dish.price),
                    "meal_type": dish.meal_type,
                    "meal_type_display": dish.get_meal_type_display(),
                    "category": dish.category,
                    "category_display": dish.get_category_display(),
                    "image": request.build_absolute_uri(dish.image.url) if dish.image else None
                }
            }, status=201)
        
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            print(f"❌ Dish creation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                "error": "Failed to create dish",
                "details": str(e)
            }, status=500)


# ==========================================
# UPDATE DISH
# ==========================================
@method_decorator(csrf_exempt, name='dispatch')
class UpdateDishView(View):
    def put(self, request, dish_id):
        try:
            dish = Dish.objects.get(id=dish_id)
            data = json.loads(request.body)
            
            # Update fields if provided
            if 'name' in data:
                dish.name = data['name'].strip()
            
            if 'secondary_name' in data:
                dish.secondary_name = data['secondary_name'].strip() or None
            
            if 'price' in data:
                try:
                    price = float(data['price'])
                    if price < 0:
                        raise ValueError("Price cannot be negative")
                    dish.price = price
                except ValueError as e:
                    return JsonResponse({"error": str(e)}, status=400)
            
            if 'meal_type' in data:
                meal_type = data['meal_type']
                valid_meal_types = [choice[0] for choice in Dish.MEAL_TYPE_CHOICES]
                if meal_type not in valid_meal_types:
                    return JsonResponse({
                        "error": f"Invalid meal_type. Must be one of: {', '.join(valid_meal_types)}"
                    }, status=400)
                dish.meal_type = meal_type
            
            if 'category' in data:
                category = data['category']
                valid_categories = [choice[0] for choice in Dish.CATEGORY_CHOICES]
                if category not in valid_categories:
                    return JsonResponse({
                        "error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"
                    }, status=400)
                
                # Check if category is allowed for meal type (skip for extras)
                if category != 'extras' and not Dish.is_category_available_for_meal(category, dish.meal_type):
                    return JsonResponse({
                        "error": f"Category '{category}' is not available for meal type '{dish.meal_type}'"
                    }, status=400)
                
                dish.category = category
            
            if 'is_active' in data:
                dish.is_active = bool(data['is_active'])
            
            dish.save()
            
            return JsonResponse({
                "message": "Dish updated successfully!",
                "dish": {
                    "id": dish.id,
                    "name": dish.name,
                    "secondary_name": dish.secondary_name,
                    "price": float(dish.price),
                    "meal_type": dish.meal_type,
                    "meal_type_display": dish.get_meal_type_display(),
                    "category": dish.category,
                    "category_display": dish.get_category_display(),
                    "is_active": dish.is_active,
                    "image": request.build_absolute_uri(dish.image.url) if dish.image else None
                }
            })
        
        except Dish.DoesNotExist:
            return JsonResponse({"error": "Dish not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# ==========================================
# DELETE DISH
# ==========================================
@method_decorator(csrf_exempt, name='dispatch')
class DeleteDishView(View):
    def delete(self, request, dish_id):
        try:
            dish = Dish.objects.get(id=dish_id)
            dish.is_active = False  # Soft delete
            dish.save()
            
            return JsonResponse({
                "message": "Dish deleted successfully!"
            })
        
        except Dish.DoesNotExist:
            return JsonResponse({"error": "Dish not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# ==========================================
# UPDATE DISH PRICE
# ==========================================
@method_decorator(csrf_exempt, name='dispatch')
class UpdateDishPriceView(View):
    def patch(self, request, dish_id):
        try:
            dish = Dish.objects.get(id=dish_id)
            data = json.loads(request.body)
            new_price = data.get('price')
            
            if new_price is None:
                return JsonResponse({
                    "error": "price is required"
                }, status=400)
            
            try:
                new_price = float(new_price)
                if new_price < 0:
                    raise ValueError("Price cannot be negative")
            except (ValueError, TypeError):
                return JsonResponse({
                    "error": "Invalid price format"
                }, status=400)
            
            dish.price = new_price
            dish.save()
            
            return JsonResponse({
                "message": "Dish price updated successfully!",
                "dish": {
                    "id": dish.id,
                    "name": dish.name,
                    "price": float(dish.price),
                    "category": dish.category,
                    "image": request.build_absolute_uri(dish.image.url) if dish.image else None
                }
            })
            
        except Dish.DoesNotExist:
            return JsonResponse({"error": "Dish not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# ==========================================
# UPDATE DISH IMAGE
# ==========================================
@method_decorator(csrf_exempt, name='dispatch')
class UpdateDishImageView(View):
    def patch(self, request, dish_id):
        try:
            dish = Dish.objects.get(id=dish_id)
            image = request.FILES.get('image')
            
            if not image:
                return JsonResponse({
                    "error": "Image file is required"
                }, status=400)
            
            # Delete old image if exists
            if dish.image:
                dish.image.delete(save=False)
            
            dish.image = image
            dish.save()
            
            return JsonResponse({
                "message": "Dish image updated successfully!",
                "dish": {
                    "id": dish.id,
                    "name": dish.name,
                    "price": float(dish.price),
                    "image": request.build_absolute_uri(dish.image.url) if dish.image else None
                }
            })
        
        except Dish.DoesNotExist:
            return JsonResponse({"error": "Dish not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# ==========================================
# CREATE ORDER - WITH EXTRAS SUPPORT
# ==========================================
@method_decorator(csrf_exempt, name='dispatch')
class CreateOrderView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            items_data = data.get('items', [])
            frontend_total = float(data.get('total_amount', 0))
            order_type = data.get('order_type', 'dine-in')
            payment_type = data.get('payment_type', 'cash')
            addons = data.get('addons', [])
            
            if not items_data:
                return JsonResponse({
                    "error": "Order must contain at least one item"
                }, status=400)
            
            # Validate order_type
            valid_order_types = [choice[0] for choice in Order.ORDER_TYPE_CHOICES]
            if order_type not in valid_order_types:
                return JsonResponse({
                    "error": f"Invalid order_type. Must be one of: {', '.join(valid_order_types)}"
                }, status=400)
            
            # Validate payment_type
            valid_payment_types = [choice[0] for choice in Order.PAYMENT_TYPE_CHOICES]
            if payment_type not in valid_payment_types:
                return JsonResponse({
                    "error": f"Invalid payment_type. Must be one of: {', '.join(valid_payment_types)}"
                }, status=400)
            
            # Create order with transaction
            with transaction.atomic():
                order = Order.objects.create(
                    total_amount=0,
                    order_type=order_type,
                    payment_type=payment_type,
                    addons=addons
                )
                
                backend_total = Decimal('0.00')
                
                # Create order items from dishes
                for item in items_data:
                    dish_id = item.get('dish_id')
                    quantity = int(item.get('quantity', 1))
                    
                    if quantity <= 0:
                        raise ValueError(f"Invalid quantity for dish {dish_id}")
                    
                    dish = Dish.objects.get(id=dish_id)
                    item_price = dish.price * quantity
                    backend_total += item_price
                    
                    OrderItem.objects.create(
                        order=order,
                        dish=dish,
                        quantity=quantity,
                        price=item_price
                    )
                
                # Add addons/extras to total
                for addon in addons:
                    addon_id = addon.get('dish_id')
                    addon_quantity = int(addon.get('quantity', 0))
                    
                    if addon_quantity > 0:
                        addon_dish = Dish.objects.get(id=addon_id)
                        # Verify it's actually an extra
                        if addon_dish.category != 'extras':
                            raise ValueError(f"Dish {addon_id} is not an extra item")
                        addon_total = addon_dish.price * addon_quantity
                        backend_total += addon_total
                        
                        # Create OrderItem for addon/extra
                        OrderItem.objects.create(
                            order=order,
                            dish=addon_dish,
                            quantity=addon_quantity,
                            price=addon_total
                        )
                
                # Verify total
                if abs(float(frontend_total) - float(backend_total)) > 0.01:
                    raise ValueError(
                        f"Total mismatch! Frontend sent ₹{frontend_total}, "
                        f"backend calculated ₹{backend_total}"
                    )
                
                order.total_amount = backend_total
                order.save()
            
            # 🖨️ PRINT BILL AFTER ORDER CREATION
            print_success = False
            print_error_message = None
            
            try:
                print_order_bill(order)
                print_success = True
                print(f"✅ Bill #{order.id} printed successfully")
            except Exception as e:
                print_error_message = str(e)
                print(f"⚠️ Printing failed for Bill #{order.id}: {e}")
                # Don't fail the order creation if printing fails
                # Just log the error and continue
            
            # Build response
            order_items = []
            for item in order.items.all():
                order_items.append({
                    "dish_name": item.dish.name,
                    "secondary_name": item.dish.secondary_name,
                    "category": item.dish.get_category_display(),
                    "quantity": item.quantity,
                    "price": float(item.price),
                    "is_extra": item.dish.category == 'extras'
                })
            
            # Separate regular items and extras for response
            regular_items = [item for item in order_items if not item['is_extra']]
            extras_list = [item for item in order_items if item['is_extra']]
            
            order_data = {
                "id": order.id,
                "order_type": order.get_order_type_display(),
                "payment_type": order.get_payment_type_display(),
                "created_at": order.created_at.isoformat(),
                "total_amount": float(order.total_amount),
                "items": regular_items,
                "extras": extras_list,
                "print_status": {
                    "success": print_success,
                    "error": print_error_message
                }
            }
            
            response_message = "Order created successfully!"
            if print_success:
                response_message += " Bill printed."
            elif print_error_message:
                response_message += f" (Print failed: {print_error_message})"
            
            return JsonResponse({
                "message": response_message,
                "order": order_data
            }, status=201)
        
        except Dish.DoesNotExist:
            return JsonResponse({"error": "Invalid dish ID"}, status=400)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"❌ Order creation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)

# ==========================================
# ORDER HISTORY VIEW
# ==========================================
@method_decorator(csrf_exempt, name='dispatch')
class OrderHistoryView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            start_time = data.get('start_time')
            end_time = data.get('end_time')
            
            if not start_time or not end_time:
                return JsonResponse({
                    "error": "start_time and end_time are required"
                }, status=400)
            
            # Parse datetime strings
            try:
                start_date = parse_datetime(start_time)
                end_date = parse_datetime(end_time)
                
                if not start_date or not end_date:
                    raise ValueError("Invalid datetime format")
                
                # Make timezone aware if needed
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
                    
            except Exception as e:
                return JsonResponse({
                    'error': f'Invalid datetime format: {str(e)}'
                }, status=400)
            
            # Query orders in date range
            orders = Order.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).prefetch_related('items__dish').order_by('-created_at')
            
            # Build response
            data = []
            for order in orders:
                order_items = []
                for item in order.items.all():
                    order_items.append({
                        "dish_name": item.dish.name,
                        "secondary_name": item.dish.secondary_name,
                        "category": item.dish.get_category_display(),
                        "quantity": item.quantity,
                        "price": float(item.price)
                    })
                
                order_info = {
                    "id": order.id,
                    "order_type": order.get_order_type_display(),
                    "payment_type": order.get_payment_type_display(),
                    "created_at": order.created_at.isoformat(),
                    "total_amount": float(order.total_amount),
                    "items": order_items,
                    "addons": order.addons or []
                }
                data.append(order_info)
            
            # Calculate summary
            total_orders = orders.count()
            total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            return JsonResponse({
                "orders": data,
                "summary": {
                    "total_orders": total_orders,
                    "total_revenue": float(total_revenue),
                    "start_time": start_date.isoformat(),
                    "end_time": end_date.isoformat()
                }
            }, safe=False)
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)


# ==========================================
# GET ORDER DETAILS BY ID
# ==========================================
class OrderDetailView(View):
    def get(self, request, order_id):
        try:
            order = Order.objects.prefetch_related('items__dish').get(id=order_id)
            
            order_items = []
            for item in order.items.all():
                order_items.append({
                    "dish_id": item.dish.id,
                    "dish_name": item.dish.name,
                    "secondary_name": item.dish.secondary_name,
                    "category": item.dish.get_category_display(),
                    "quantity": item.quantity,
                    "unit_price": float(item.dish.price),
                    "subtotal": float(item.price)
                })
            
            order_data = {
                "id": order.id,
                "order_type": order.get_order_type_display(),
                "payment_type": order.get_payment_type_display(),
                "created_at": order.created_at.isoformat(),
                "total_amount": float(order.total_amount),
                "items": order_items,
                "addons": order.addons or []
            }
            
            return JsonResponse(order_data)
        
        except Order.DoesNotExist:
            return JsonResponse({"error": "Order not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



# ==========================================
# DISH SALES IN PERIOD
# ==========================================
@csrf_exempt
def dish_sales_in_period(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        body = json.loads(request.body)
        start = body.get('start')
        end = body.get('end')
        dish_id = body.get('dish_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)

    if not start or not end:
        return JsonResponse({'error': 'Missing required fields: start and end'}, status=400)

    try:
        start_date = parse_datetime(start)
        end_date = parse_datetime(end)
        if not start_date or not end_date:
            raise ValueError
    except Exception:
        return JsonResponse({'error': 'Invalid datetime format. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS)'}, status=400)

    # ORM aggregation to count sold quantity
    total_sales = (
        OrderItem.objects
        .filter(dish_id=dish_id, order__created_at__range=[start_date, end_date])
        .aggregate(total_quantity=Sum('quantity'))['total_quantity']
    ) or 0

    return JsonResponse({
        'dish_id': dish_id,
        'start': start,
        'end': end,
        'total_quantity_sold': total_sales
    })

# expenditure

def get_date_range(filter_type, start_date_str=None, end_date_str=None):
    today = timezone.now().date()
    if filter_type == 'today':
        return today,  today 
    elif filter_type == 'week':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end
    elif filter_type == 'month':
        start = today.replace(day=1)
        end = today
        return start, end
    elif start_date_str and end_date_str:
        return parse_date(start_date_str), parse_date(end_date_str)
    else:
        return None, None

# ==========================================
# WORKER VIEWS
# ==========================================
class WorkerListView(View):
    def get(self, request):
        try:
            workers = Worker.objects.filter(is_active=True).order_by('name')
            
            data = [{
                'id': worker.id,
                'name': worker.name,
                'role': worker.role,
                'role_display': worker.get_role_display(),
                'contact': worker.contact,
                'joined_date': worker.joined_date.isoformat() if worker.joined_date else None,
            } for worker in workers]
            
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class WorkerCreateView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            worker = Worker.objects.create(
                name=data.get('name'),
                role=data.get('role', 'worker'),
                contact=data.get('contact', '')
            )
            
            return JsonResponse({
                'success': True,
                'worker': {
                    'id': worker.id,
                    'name': worker.name,
                    'role': worker.role,
                    'role_display': worker.get_role_display()
                }
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


# ==========================================
# MATERIAL VIEWS
# ==========================================
class MaterialListView(View):
    def get(self, request):
        try:
            materials = Material.objects.filter(is_active=True).order_by('name')
            
            data = [{
                'id': material.id,
                'name': material.name,
                'unit': material.unit,
                'unit_display': material.get_unit_display(),
                'description': material.description,
            } for material in materials]
            
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class MaterialCreateView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            material = Material.objects.create(
                name=data.get('name'),
                unit=data.get('unit', 'piece'),
                description=data.get('description', '')
            )
            
            return JsonResponse({
                'success': True,
                'material': {
                    'id': material.id,
                    'name': material.name,
                    'unit': material.unit,
                    'unit_display': material.get_unit_display()
                }
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


# ==========================================
# EXPENSE VIEWS
# ==========================================
@method_decorator(csrf_exempt, name='dispatch')
class ExpenseFilterView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            filter_type = data.get('filter_type', 'today')
            expense_type = data.get('expense_type', 'all')  # 'all', 'worker', 'material'
            
            # Date filtering
            today = datetime.now().date()
            if filter_type == 'today':
                start_date = today
                end_date = today
            elif filter_type == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = today
            elif filter_type == 'month':
                start_date = today.replace(day=1)
                end_date = today
            elif filter_type == 'custom':
                start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
                end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
            else:
                start_date = today
                end_date = today
            
            # Query expenses
            expenses = Expense.objects.filter(
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            )
            
            # Filter by expense type
            if expense_type == 'worker':
                expenses = expenses.filter(expense_type='worker')
            elif expense_type == 'material':
                expenses = expenses.filter(expense_type='material')
            
            expenses = expenses.select_related('worker').prefetch_related('items__material')
            
            # Build response
            expenses_data = []
            for expense in expenses:
                expense_dict = {
                    'id': expense.id,
                    'expense_type': expense.expense_type,
                    'expense_type_display': expense.get_expense_type_display(),
                    'description': expense.description,
                    'total_amount': str(expense.total_amount),
                    'timestamp': expense.timestamp.isoformat(),
                    'notes': expense.notes,
                }
                
                if expense.expense_type == 'worker' and expense.worker:
                    expense_dict.update({
                        'worker': expense.worker.name,
                        'worker_id': expense.worker.id,
                        'worker_role': expense.worker.get_role_display(),
                        'category': expense.worker_category,
                        'category_display': expense.get_worker_category_display() if expense.worker_category else 'N/A',
                    })
                elif expense.expense_type == 'material':
                    items = [{
                        'material': item.material.name,
                        'material_id': item.material.id,
                        'quantity': str(item.quantity),
                        'unit': item.material.get_unit_display(),
                        'unit_price': str(item.unit_price),
                        'subtotal': str(item.subtotal),
                    } for item in expense.items.all()]
                    expense_dict['items'] = items
                
                expenses_data.append(expense_dict)
            
            # Calculate summaries
            total_amount = expenses.aggregate(total=Sum('total_amount'))['total'] or 0
            
            worker_total = expenses.filter(expense_type='worker').aggregate(
                total=Sum('total_amount'))['total'] or 0
            
            material_total = expenses.filter(expense_type='material').aggregate(
                total=Sum('total_amount'))['total'] or 0
            
            # Worker-wise summary
            worker_summary = {}
            for expense in expenses.filter(expense_type='worker'):
                if expense.worker:
                    worker_name = expense.worker.name
                    if worker_name not in worker_summary:
                        worker_summary[worker_name] = {
                            'worker_id': expense.worker.id,
                            'role': expense.worker.get_role_display(),
                            'total': 0,
                            'count': 0
                        }
                    worker_summary[worker_name]['total'] += float(expense.total_amount)
                    worker_summary[worker_name]['count'] += 1
            
            # Material-wise summary
            material_summary = {}
            for expense in expenses.filter(expense_type='material'):
                for item in expense.items.all():
                    material_name = item.material.name
                    if material_name not in material_summary:
                        material_summary[material_name] = {
                            'material_id': item.material.id,
                            'unit': item.material.get_unit_display(),
                            'total_quantity': 0,
                            'total_amount': 0,
                            'count': 0
                        }
                    material_summary[material_name]['total_quantity'] += float(item.quantity)
                    material_summary[material_name]['total_amount'] += float(item.subtotal)
                    material_summary[material_name]['count'] += 1
            
            return JsonResponse({
                'expenses': expenses_data,
                'summary': {
                    'total_amount': str(total_amount),
                    'worker_total': str(worker_total),
                    'material_total': str(material_total),
                    'total_count': len(expenses_data),
                    'worker_count': len([e for e in expenses_data if e['expense_type'] == 'worker']),
                    'material_count': len([e for e in expenses_data if e['expense_type'] == 'material']),
                },
                'worker_summary': worker_summary,
                'material_summary': material_summary,
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'filter_type': filter_type
                }
            })
        
        except Exception as e:
            import traceback
            print("Error in ExpenseFilterView:")
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AddWorkerExpenseView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            worker_id = data.get('worker_id')
            category = data.get('category', 'wage')
            description = data.get('description', '')
            amount = data.get('amount')
            
            if not worker_id or not amount:
                return JsonResponse({"error": "Worker and amount are required"}, status=400)
            
            worker = Worker.objects.get(id=worker_id)
            
            expense = Expense.objects.create(
                expense_type='worker',
                worker=worker,
                worker_category=category,
                description=description or f"{category.title()} - {worker.name}",
                total_amount=amount
            )
            
            return JsonResponse({
                'success': True,
                'expense': {
                    'id': expense.id,
                    'worker': worker.name,
                    'category': expense.get_worker_category_display(),
                    'amount': str(expense.total_amount)
                }
            })
        
        except Worker.DoesNotExist:
            return JsonResponse({"error": "Worker not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class AddMaterialExpenseView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            description = data.get('description', 'Material Purchase')
            items_data = data.get('items', [])
            
            if not items_data:
                return JsonResponse({"error": "At least one material item is required"}, status=400)
            
            with transaction.atomic():
                # Create expense
                expense = Expense.objects.create(
                    expense_type='material',
                    description=description,
                    total_amount=0  # Will be calculated from items
                )
                
                # Create expense items
                for item_data in items_data:
                    material = Material.objects.get(id=item_data['material_id'])
                    
                    ExpenseItem.objects.create(
                        expense=expense,
                        material=material,
                        quantity=item_data['quantity'],
                        unit_price=item_data['unit_price']
                    )
                
                # Recalculate total
                expense.save()
                
                return JsonResponse({
                    'success': True,
                    'expense': {
                        'id': expense.id,
                        'description': expense.description,
                        'total_amount': str(expense.total_amount),
                        'items_count': len(items_data)
                    }
                })
        
        except Material.DoesNotExist:
            return JsonResponse({"error": "Material not found"}, status=404)
        except Exception as e:
            import traceback
            print("Error in AddMaterialExpenseView:")
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=400)


# ==========================================
# COMPLETE ANALYTICS DASHBOARD VIEW
# ==========================================
class AnalyticsDashboardView(APIView):
    """
    Complete analytics dashboard with shift-wise analysis
    Requires authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get date parameters
            date_str = request.GET.get('date')
            filter_type = request.GET.get('filter', 'today')
            
            if filter_type == 'today' or not date_str:
                target_date = datetime.now().date()
            elif filter_type == 'yesterday':
                target_date = (datetime.now() - timedelta(days=1)).date()
            else:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Shift times
            morning_start = datetime.combine(target_date, time(7, 0))
            morning_end = datetime.combine(target_date, time(16, 0))
            night_start = datetime.combine(target_date, time(16, 0))
            night_end = datetime.combine(target_date + timedelta(days=1), time(2, 0))
            
            # Previous day closing for opening balance
            previous_date = target_date - timedelta(days=1)
            previous_night_start = datetime.combine(previous_date, time(16, 0))
            previous_night_end = datetime.combine(target_date, time(2, 0))
            
            previous_revenue = Order.objects.filter(
                created_at__gte=previous_night_start,
                created_at__lt=previous_night_end
            ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']
            
            previous_expenses = Expense.objects.filter(
                timestamp__gte=previous_night_start,
                timestamp__lt=previous_night_end
            ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']
            
            opening_balance = previous_revenue - previous_expenses
            
            # MORNING SHIFT
            morning_orders = Order.objects.filter(
                created_at__gte=morning_start,
                created_at__lt=morning_end
            )
            
            morning_revenue = morning_orders.aggregate(
                total=Coalesce(Sum('total_amount'), Decimal('0.00'))
            )['total']
            morning_order_count = morning_orders.count()
            morning_expenses = Expense.objects.filter(
                timestamp__gte=morning_start,
                timestamp__lt=morning_end
            ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']
            morning_profit = morning_revenue - morning_expenses
            morning_closing = opening_balance + morning_profit
            
            # Morning top dishes
            morning_top_dishes = OrderItem.objects.filter(
                order__created_at__gte=morning_start,
                order__created_at__lt=morning_end
            ).values(
                'dish__id',
                'dish__name',
                'dish__secondary_name',
                'dish__category',
                'dish__meal_type',
                'dish__price'
            ).annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('price'), output_field=DecimalField()),
                order_count=Count('order', distinct=True)
            ).order_by('-total_quantity')[:10]
            
            # NIGHT SHIFT
            night_orders = Order.objects.filter(
                created_at__gte=night_start,
                created_at__lt=night_end
            )
            
            night_revenue = night_orders.aggregate(
                total=Coalesce(Sum('total_amount'), Decimal('0.00'))
            )['total']
            night_order_count = night_orders.count()
            night_expenses = Expense.objects.filter(
                timestamp__gte=night_start,
                timestamp__lt=night_end
            ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']
            night_profit = night_revenue - night_expenses
            night_opening = morning_closing
            night_closing = night_opening + night_profit
            
            # Night top dishes
            night_top_dishes = OrderItem.objects.filter(
                order__created_at__gte=night_start,
                order__created_at__lt=night_end
            ).values(
                'dish__id',
                'dish__name',
                'dish__secondary_name',
                'dish__category',
                'dish__meal_type',
                'dish__price'
            ).annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('price'), output_field=DecimalField()),
                order_count=Count('order', distinct=True)
            ).order_by('-total_quantity')[:10]
            
            # OVERALL
            total_revenue = morning_revenue + night_revenue
            total_expenses = morning_expenses + night_expenses
            total_profit = total_revenue - total_expenses
            total_orders = morning_order_count + night_order_count
            
            # Overall top dishes
            overall_top_dishes = OrderItem.objects.filter(
                Q(order__created_at__gte=morning_start, order__created_at__lt=morning_end) |
                Q(order__created_at__gte=night_start, order__created_at__lt=night_end)
            ).values(
                'dish__id',
                'dish__name',
                'dish__secondary_name',
                'dish__category',
                'dish__meal_type',
                'dish__price'
            ).annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('price'), output_field=DecimalField()),
                order_count=Count('order', distinct=True)
            ).order_by('-total_quantity')[:10]
            
            # Expense breakdown
            morning_expense_breakdown = Expense.objects.filter(
                timestamp__gte=morning_start,
                timestamp__lt=morning_end
            ).values('expense_type').annotate(total=Sum('total_amount'))
            
            night_expense_breakdown = Expense.objects.filter(
                timestamp__gte=night_start,
                timestamp__lt=night_end
            ).values('expense_type').annotate(total=Sum('total_amount'))
            
            # Payment breakdown
            morning_payment_breakdown = morning_orders.values('payment_type').annotate(
                count=Count('id'),
                total=Sum('total_amount')
            )
            
            night_payment_breakdown = night_orders.values('payment_type').annotate(
                count=Count('id'),
                total=Sum('total_amount')
            )
            
            # Order type breakdown
            morning_order_type = morning_orders.values('order_type').annotate(
                count=Count('id'),
                total=Sum('total_amount')
            )
            
            night_order_type = night_orders.values('order_type').annotate(
                count=Count('id'),
                total=Sum('total_amount')
            )
            
            # Average order value
            morning_avg_order = morning_revenue / morning_order_count if morning_order_count > 0 else Decimal('0.00')
            night_avg_order = night_revenue / night_order_count if night_order_count > 0 else Decimal('0.00')
            
            return Response({
                'date': target_date.isoformat(),
                'filter_type': filter_type,
                'opening_balance': str(opening_balance),
                
                'morning_shift': {
                    'start_time': morning_start.strftime('%I:%M %p'),
                    'end_time': morning_end.strftime('%I:%M %p'),
                    'opening_balance': str(opening_balance),
                    'revenue': str(morning_revenue),
                    'expenses': str(morning_expenses),
                    'profit': str(morning_profit),
                    'closing_balance': str(morning_closing),
                    'order_count': morning_order_count,
                    'avg_order_value': str(morning_avg_order),
                    'top_dishes': [
                        {
                            'dish_id': dish['dish__id'],
                            'name': dish['dish__name'],
                            'secondary_name': dish['dish__secondary_name'],
                            'category': dish['dish__category'],
                            'meal_type': dish['dish__meal_type'],
                            'price': str(dish['dish__price']),
                            'quantity_sold': dish['total_quantity'],
                            'total_revenue': str(dish['total_revenue']),
                            'order_count': dish['order_count']
                        }
                        for dish in morning_top_dishes
                    ],
                    'expense_breakdown': {
                        item['expense_type']: str(item['total'])
                        for item in morning_expense_breakdown
                    },
                    'payment_breakdown': list(morning_payment_breakdown),
                    'order_type_breakdown': list(morning_order_type)
                },
                
                'night_shift': {
                    'start_time': night_start.strftime('%I:%M %p'),
                    'end_time': night_end.strftime('%I:%M %p'),
                    'opening_balance': str(night_opening),
                    'revenue': str(night_revenue),
                    'expenses': str(night_expenses),
                    'profit': str(night_profit),
                    'closing_balance': str(night_closing),
                    'order_count': night_order_count,
                    'avg_order_value': str(night_avg_order),
                    'top_dishes': [
                        {
                            'dish_id': dish['dish__id'],
                            'name': dish['dish__name'],
                            'secondary_name': dish['dish__secondary_name'],
                            'category': dish['dish__category'],
                            'meal_type': dish['dish__meal_type'],
                            'price': str(dish['dish__price']),
                            'quantity_sold': dish['total_quantity'],
                            'total_revenue': str(dish['total_revenue']),
                            'order_count': dish['order_count']
                        }
                        for dish in night_top_dishes
                    ],
                    'expense_breakdown': {
                        item['expense_type']: str(item['total'])
                        for item in night_expense_breakdown
                    },
                    'payment_breakdown': list(night_payment_breakdown),
                    'order_type_breakdown': list(night_order_type)
                },
                
                'overall': {
                    'total_revenue': str(total_revenue),
                    'total_expenses': str(total_expenses),
                    'total_profit': str(total_profit),
                    'total_orders': total_orders,
                    'final_closing_balance': str(night_closing),
                    'top_dishes': [
                        {
                            'dish_id': dish['dish__id'],
                            'name': dish['dish__name'],
                            'secondary_name': dish['dish__secondary_name'],
                            'category': dish['dish__category'],
                            'meal_type': dish['dish__meal_type'],
                            'price': str(dish['dish__price']),
                            'quantity_sold': dish['total_quantity'],
                            'total_revenue': str(dish['total_revenue']),
                            'order_count': dish['order_count']
                        }
                        for dish in overall_top_dishes
                    ]
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            import traceback
            print("Error in AnalyticsDashboardView:")
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================
# CATEGORY PERFORMANCE VIEW
# ==========================================
class CategoryPerformanceView(APIView):
    """
    Analyze sales performance by dish category
    Requires authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            date_str = request.GET.get('date')
            filter_type = request.GET.get('filter', 'today')
            
            if filter_type == 'today' or not date_str:
                target_date = datetime.now().date()
            elif filter_type == 'yesterday':
                target_date = (datetime.now() - timedelta(days=1)).date()
            else:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            start_datetime = datetime.combine(target_date, time(7, 0))
            end_datetime = datetime.combine(target_date + timedelta(days=1), time(2, 0))
            
            # Category-wise performance
            category_stats = OrderItem.objects.filter(
                order__created_at__gte=start_datetime,
                order__created_at__lt=end_datetime
            ).values(
                'dish__category'
            ).annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('price'), output_field=DecimalField()),
                order_count=Count('order', distinct=True),
                dish_count=Count('dish', distinct=True)
            ).order_by('-total_revenue')
            
            # Calculate percentages
            total_revenue = sum(Decimal(str(cat['total_revenue'])) for cat in category_stats)
            
            results = []
            for cat in category_stats:
                revenue = Decimal(str(cat['total_revenue']))
                percentage = (revenue / total_revenue * 100) if total_revenue > 0 else Decimal('0')
                
                results.append({
                    'category': cat['dish__category'],
                    'category_display': dict(Dish.CATEGORY_CHOICES).get(cat['dish__category'], cat['dish__category']),
                    'total_quantity': cat['total_quantity'],
                    'total_revenue': str(revenue),
                    'revenue_percentage': str(round(percentage, 2)),
                    'order_count': cat['order_count'],
                    'unique_dishes_sold': cat['dish_count']
                })
            
            return Response({
                'date': target_date.isoformat(),
                'categories': results,
                'total_revenue': str(total_revenue)
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================
# HOURLY TRENDS VIEW
# ==========================================
class HourlyTrendsView(APIView):
    """
    Hour-by-hour sales analysis
    Requires authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            date_str = request.GET.get('date')
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
            
            start_datetime = datetime.combine(target_date, time(7, 0))
            end_datetime = datetime.combine(target_date + timedelta(days=1), time(2, 0))
            
            # Hourly breakdown
            hourly_data = Order.objects.filter(
                created_at__gte=start_datetime,
                created_at__lt=end_datetime
            ).annotate(
                hour=TruncHour('created_at')
            ).values('hour').annotate(
                order_count=Count('id'),
                total_revenue=Sum('total_amount')
            ).order_by('hour')
            
            results = []
            for item in hourly_data:
                hour_time = item['hour']
                results.append({
                    'hour': hour_time.strftime('%I:00 %p'),
                    'hour_24': hour_time.hour,
                    'order_count': item['order_count'],
                    'revenue': str(item['total_revenue'])
                })
            
            return Response({
                'date': target_date.isoformat(),
                'hourly_data': results
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================
# COMPARISON VIEW
# ==========================================
class ComparisonView(APIView):
    """
    Compare today vs yesterday / this week vs last week
    Requires authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            comparison_type = request.GET.get('type', 'day')  # 'day' or 'week'
            
            if comparison_type == 'day':
                today = datetime.now().date()
                yesterday = today - timedelta(days=1)
                
                today_start = datetime.combine(today, time(7, 0))
                today_end = datetime.combine(today + timedelta(days=1), time(2, 0))
                yesterday_start = datetime.combine(yesterday, time(7, 0))
                yesterday_end = datetime.combine(yesterday + timedelta(days=1), time(2, 0))
                
                today_revenue = Order.objects.filter(
                    created_at__gte=today_start,
                    created_at__lt=today_end
                ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']
                
                yesterday_revenue = Order.objects.filter(
                    created_at__gte=yesterday_start,
                    created_at__lt=yesterday_end
                ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']
                
                today_orders = Order.objects.filter(
                    created_at__gte=today_start,
                    created_at__lt=today_end
                ).count()
                
                yesterday_orders = Order.objects.filter(
                    created_at__gte=yesterday_start,
                    created_at__lt=yesterday_end
                ).count()
                
                revenue_change = ((today_revenue - yesterday_revenue) / yesterday_revenue * 100) if yesterday_revenue > 0 else Decimal('0')
                orders_change = ((today_orders - yesterday_orders) / yesterday_orders * 100) if yesterday_orders > 0 else 0
                
                return Response({
                    'comparison_type': 'day',
                    'current': {
                        'date': today.isoformat(),
                        'revenue': str(today_revenue),
                        'orders': today_orders
                    },
                    'previous': {
                        'date': yesterday.isoformat(),
                        'revenue': str(yesterday_revenue),
                        'orders': yesterday_orders
                    },
                    'change': {
                        'revenue_percentage': str(round(revenue_change, 2)),
                        'orders_percentage': str(round(orders_change, 2)),
                        'revenue_difference': str(today_revenue - yesterday_revenue),
                        'orders_difference': today_orders - yesterday_orders
                    }
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================
# LOW PERFORMING DISHES VIEW
# ==========================================
class LowPerformingDishesView(APIView):
    """
    Identify dishes with low sales
    Requires authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            days = int(request.GET.get('days', 7))
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get dishes with low sales
            dishes_with_sales = OrderItem.objects.filter(
                order__created_at__gte=start_date,
                order__created_at__lt=end_date
            ).values(
                'dish__id',
                'dish__name',
                'dish__secondary_name',
                'dish__category',
                'dish__price'
            ).annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('price'), output_field=DecimalField())
            ).order_by('total_quantity')[:10]
            
            # Dishes with zero sales
            sold_dish_ids = OrderItem.objects.filter(
                order__created_at__gte=start_date,
                order__created_at__lt=end_date
            ).values_list('dish__id', flat=True).distinct()
            
            zero_sales_dishes = Dish.objects.filter(
                is_active=True
            ).exclude(
                id__in=sold_dish_ids
            ).values(
                'id',
                'name',
                'secondary_name',
                'category',
                'price'
            )[:10]
            
            return Response({
                'period_days': days,
                'start_date': start_date.date().isoformat(),
                'end_date': end_date.date().isoformat(),
                'low_sales_dishes': [
                    {
                        'dish_id': dish['dish__id'],
                        'name': dish['dish__name'],
                        'secondary_name': dish['dish__secondary_name'],
                        'category': dish['dish__category'],
                        'price': str(dish['dish__price']),
                        'quantity_sold': dish['total_quantity'],
                        'total_revenue': str(dish['total_revenue'])
                    }
                    for dish in dishes_with_sales
                ],
                'zero_sales_dishes': [
                    {
                        'dish_id': dish['id'],
                        'name': dish['name'],
                        'secondary_name': dish['secondary_name'],
                        'category': dish['category'],
                        'price': str(dish['price'])
                    }
                    for dish in zero_sales_dishes
                ]
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================
# WORKER EXPENSE BREAKDOWN VIEW
# ==========================================
class WorkerExpenseBreakdownView(APIView):
    """
    Detailed worker expense analysis
    Requires authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            date_str = request.GET.get('date')
            filter_type = request.GET.get('filter', 'today')
            
            if filter_type == 'today' or not date_str:
                target_date = datetime.now().date()
            elif filter_type == 'yesterday':
                target_date = (datetime.now() - timedelta(days=1)).date()
            else:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            start_datetime = datetime.combine(target_date, time(0, 0))
            end_datetime = datetime.combine(target_date + timedelta(days=1), time(0, 0))
            
            # Worker-wise expenses
            worker_expenses = Expense.objects.filter(
                expense_type='worker',
                timestamp__gte=start_datetime,
                timestamp__lt=end_datetime
            ).values(
                'worker__id',
                'worker__name',
                'worker__role',
                'worker_category'
            ).annotate(
                total_amount=Sum('total_amount'),
                transaction_count=Count('id')
            ).order_by('-total_amount')
            
            # Category-wise breakdown
            category_breakdown = Expense.objects.filter(
                expense_type='worker',
                timestamp__gte=start_datetime,
                timestamp__lt=end_datetime
            ).values('worker_category').annotate(
                total=Sum('total_amount'),
                count=Count('id')
            ).order_by('-total')
            
            total_worker_expense = sum(item['total_amount'] for item in worker_expenses)
            
            return Response({
                'date': target_date.isoformat(),
                'total_worker_expense': str(total_worker_expense),
                'worker_breakdown': [
                    {
                        'worker_id': item['worker__id'],
                        'worker_name': item['worker__name'],
                        'worker_role': item['worker__role'],
                        'category': item['worker_category'],
                        'total_amount': str(item['total_amount']),
                        'transaction_count': item['transaction_count']
                    }
                    for item in worker_expenses
                ],
                'category_breakdown': [
                    {
                        'category': item['worker_category'],
                        'total': str(item['total']),
                        'count': item['count']
                    }
                    for item in category_breakdown
                ]
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================
# MATERIAL EXPENSE BREAKDOWN VIEW
# ==========================================
class MaterialExpenseBreakdownView(APIView):
    """
    Detailed material expense analysis
    Requires authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            date_str = request.GET.get('date')
            filter_type = request.GET.get('filter', 'today')
            
            if filter_type == 'today' or not date_str:
                target_date = datetime.now().date()
            elif filter_type == 'yesterday':
                target_date = (datetime.now() - timedelta(days=1)).date()
            else:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            start_datetime = datetime.combine(target_date, time(0, 0))
            end_datetime = datetime.combine(target_date + timedelta(days=1), time(0, 0))
            
            # Material-wise expenses
            material_expenses = ExpenseItem.objects.filter(
                expense__expense_type='material',
                expense__timestamp__gte=start_datetime,
                expense__timestamp__lt=end_datetime
            ).values(
                'material__id',
                'material__name',
                'material__unit'
            ).annotate(
                total_quantity=Sum('quantity'),
                total_amount=Sum('subtotal'),
                purchase_count=Count('expense', distinct=True),
                avg_unit_price=Avg('unit_price')
            ).order_by('-total_amount')
            
            total_material_expense = sum(item['total_amount'] for item in material_expenses)
            
            return Response({
                'date': target_date.isoformat(),
                'total_material_expense': str(total_material_expense),
                'material_breakdown': [
                    {
                        'material_id': item['material__id'],
                        'material_name': item['material__name'],
                        'unit': item['material__unit'],
                        'total_quantity': str(item['total_quantity']),
                        'total_amount': str(item['total_amount']),
                        'purchase_count': item['purchase_count'],
                        'avg_unit_price': str(item['avg_unit_price'])
                    }
                    for item in material_expenses
                ]
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================
# WEEKLY SUMMARY VIEW
# ==========================================
class WeeklySummaryView(APIView):
    """
    7-day summary report
    Requires authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=6)
            
            daily_summary = []
            total_revenue = Decimal('0.00')
            total_expenses = Decimal('0.00')
            total_orders = 0
            
            current_date = start_date
            while current_date <= end_date:
                day_start = datetime.combine(current_date, time(7, 0))
                day_end = datetime.combine(current_date + timedelta(days=1), time(2, 0))
                
                day_revenue = Order.objects.filter(
                    created_at__gte=day_start,
                    created_at__lt=day_end
                ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']
                
                day_expenses = Expense.objects.filter(
                    timestamp__gte=day_start,
                    timestamp__lt=day_end
                ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']
                
                day_orders = Order.objects.filter(
                    created_at__gte=day_start,
                    created_at__lt=day_end
                ).count()
                
                daily_summary.append({
                    'date': current_date.isoformat(),
                    'day_name': current_date.strftime('%A'),
                    'revenue': str(day_revenue),
                    'expenses': str(day_expenses),
                    'profit': str(day_revenue - day_expenses),
                    'orders': day_orders
                })
                
                total_revenue += day_revenue
                total_expenses += day_expenses
                total_orders += day_orders
                
                current_date += timedelta(days=1)
            
            # Best day
            best_day = max(daily_summary, key=lambda x: Decimal(x['revenue'])) if daily_summary else None
            
            return Response({
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
                'summary': {
                    'total_revenue': str(total_revenue),
                    'total_expenses': str(total_expenses),
                    'total_profit': str(total_revenue - total_expenses),
                    'total_orders': total_orders,
                    'avg_daily_revenue': str(total_revenue / 7),
                    'avg_daily_orders': round(total_orders / 7, 2)
                },
                'daily_breakdown': daily_summary,
                'best_day': best_day
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)