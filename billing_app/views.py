from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator
from django.forms.models import model_to_dict
from django.db.models import F, Sum, DecimalField,Count
from .models import *
import json
from django.utils.dateparse import parse_datetime,parse_date
from .print_utils import print_order_bill 
from django.utils import timezone
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import date
from rest_framework.views import APIView
from datetime import datetime, timedelta
from decimal import Decimal
# ==========================================
# GET ALL DISHES WITH FILTERING
# ==========================================
class DishListView(View):
    def get(self, request):
        try:
            # Get filter parameters
            meal_type = request.GET.get('meal_type', None)
            dish_type = request.GET.get('dish_type', None)
            
            # Start with all active dishes
            dishes = Dish.objects.filter(is_active=True)
            
            # Filter by meal_type if provided
            if meal_type:
                valid_meal_types = [choice[0] for choice in Dish.MEAL_TYPE_CHOICES]
                if meal_type not in valid_meal_types:
                    return JsonResponse({
                        "error": f"Invalid meal_type. Must be one of: {', '.join(valid_meal_types)}"
                    }, status=400)
                dishes = dishes.filter(meal_type=meal_type)
            
            # Filter by dish_type if provided
            if dish_type:
                valid_dish_types = [choice[0] for choice in Dish.DISH_TYPE_CHOICES]
                if dish_type not in valid_dish_types:
                    return JsonResponse({
                        "error": f"Invalid dish_type. Must be one of: {', '.join(valid_dish_types)}"
                    }, status=400)
                dishes = dishes.filter(dish_type=dish_type)
            
            # Order results
            dishes = dishes.order_by('dish_type', 'name')
            
            # Build response data
            data = []
            for dish in dishes:
                data.append({
                    'id': dish.id,
                    'name': dish.name,
                    'secondary_name': dish.secondary_name,
                    'price': float(dish.price),
                    'meal_type': dish.meal_type,
                    'meal_type_display': dish.get_meal_type_display(),
                    'dish_type': dish.dish_type,
                    'dish_type_display': dish.get_dish_type_display(),
                    'image': request.build_absolute_uri(dish.image.url) if dish.image else None,
                    'is_active': dish.is_active,
                    'created_at': dish.created_at.isoformat(),
                })
            
            return JsonResponse(data, safe=False)
        
        except Exception as e:
            return JsonResponse({
                "error": str(e)
            }, status=500)


# ==========================================
# GET DISH TYPES (for filtering)
# ==========================================
class DishTypesView(View):
    def get(self, request):
        try:
            dish_types = [
                {
                    'value': choice[0],
                    'label': choice[1]
                }
                for choice in Dish.DISH_TYPE_CHOICES
            ]
            return JsonResponse(dish_types, safe=False)
        except Exception as e:
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
                "dish_type": dish.dish_type,
                "dish_type_display": dish.get_dish_type_display(),
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


# ==========================================
# CREATE DISH
# ==========================================
@method_decorator(csrf_exempt, name='dispatch')
class CreateDishView(View):
    def post(self, request):
        try:
            name = request.POST.get('name', '').strip()
            secondary_name = request.POST.get('secondary_name', '').strip()
            price = request.POST.get('price', '').strip()
            meal_type = request.POST.get('meal_type', 'afternoon').strip()
            dish_type = request.POST.get('dish_type', 'meals').strip()
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
            
            # Validate dish_type
            valid_dish_types = [choice[0] for choice in Dish.DISH_TYPE_CHOICES]
            if dish_type not in valid_dish_types:
                return JsonResponse({
                    "error": f"Invalid dish_type. Must be one of: {', '.join(valid_dish_types)}"
                }, status=400)
            
            # Create dish
            dish = Dish.objects.create(
                name=name,
                secondary_name=secondary_name if secondary_name else None,
                price=price_float,
                meal_type=meal_type,
                dish_type=dish_type,
                image=image
            )
            
            return JsonResponse({
                "message": "Dish created successfully!",
                "dish": {
                    "id": dish.id,
                    "name": dish.name,
                    "secondary_name": dish.secondary_name or "",
                    "price": float(dish.price),
                    "meal_type": dish.meal_type,
                    "meal_type_display": dish.get_meal_type_display(),
                    "dish_type": dish.dish_type,
                    "dish_type_display": dish.get_dish_type_display(),
                    "image": request.build_absolute_uri(dish.image.url) if dish.image else None
                }
            }, status=201)
        
        except Exception as e:
            print(f"❌ Dish creation error: {str(e)}")
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
                    "dish_type": dish.dish_type,
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
# CREATE ORDER
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
            
            # Create order
            order = Order.objects.create(
                total_amount=0,
                order_type=order_type,
                payment_type=payment_type,
                addons=addons
            )
            
            backend_total = 0
            
            # Create order items from dishes
            for item in items_data:
                dish_id = item.get('dish_id')
                quantity = int(item.get('quantity', 1))
                dish = Dish.objects.get(id=dish_id)
                price = dish.price * quantity
                backend_total += float(price)
                
                OrderItem.objects.create(
                    order=order,
                    dish=dish,
                    quantity=quantity,
                    price=price
                )
            
            # Add addons to total
            for addon in addons:
                addon_total = float(addon.get('price', 0)) * int(addon.get('quantity', 0))
                backend_total += addon_total
            
            # Verify total
            if abs(frontend_total - backend_total) > 0.01:  # Allow small floating point difference
                order.delete()
                return JsonResponse({
                    "error": f"Total mismatch! Frontend sent {frontend_total}, backend calculated {backend_total}"
                }, status=400)
            
            order.total_amount = backend_total
            order.save()
            
            # Print bill (if you have printer setup)
            try:
                # Uncomment if you have print_order_bill function
                # print_order_bill(order)
                pass
            except Exception as e:
                print("⚠️ Printing failed:", e)
            
            # Build response
            order_data = {
                "id": order.id,
                "order_type": order.get_order_type_display(),
                "payment_type": order.get_payment_type_display(),
                "created_at": order.created_at.isoformat(),
                "total_amount": float(order.total_amount),
                "items": [
                    {
                        "dish_name": item.dish.name,
                        "secondary_name": item.dish.secondary_name,
                        "dish_type": item.dish.get_dish_type_display(),
                        "quantity": item.quantity,
                        "price": float(item.price)
                    }
                    for item in order.items.all()
                ],
                "addons": addons
            }
            
            return JsonResponse({
                "message": "Order created successfully!",
                "order": order_data
            }, status=201)
        
        except Dish.DoesNotExist:
            return JsonResponse({"error": "Invalid dish ID"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
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
            
            # Query orders in date range - NO LIMIT!
            orders = Order.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).order_by('-created_at')
            
            # Log for debugging
            # print(f"📅 Querying orders between {start_date} and {end_date}")
            # print(f"✅ Found {orders.count()} orders")
            
            # Build response
            data = []
            for order in orders:
                order_info = {
                    "id": order.id,
                    "order_type": order.get_order_type_display(),
                    "created_at": order.created_at.isoformat(),
                    "total_amount": float(order.total_amount),
                    "items": [
                        {
                            "dish_name": item.dish.name,
                            "quantity": item.quantity,
                            "price": float(item.price)
                        }
                        for item in order.items.all()
                    ]
                }
                data.append(order_info)
            
            return JsonResponse(data, safe=False)
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
# 1️⃣ Total sales quantity for a dish within a time range
# billing/views.py
# from django.views.decorators.csrf import csrf_exempt
# from django.utils.dateparse import parse_datetime
# from django.http import JsonResponse
# from django.db.models import Sum
# import json
# from .models import OrderItem


@csrf_exempt
def dish_sales_in_period(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        body = json.loads(request.body)
        start = body.get('start')
        end = body.get('end')
        dish_id=body.get('dish_id')
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
    
# billing/views.py (continued)


@method_decorator(csrf_exempt, name='dispatch')
class UpdateDishImageView(View):
    def patch(self, request, dish_id):
        try:
            dish = Dish.objects.get(id=dish_id)

            # Check for uploaded file in multipart/form-data
            image = request.FILES.get('image')
            if not image:
                return JsonResponse({
                    "error": "Image file is required"
                }, status=400)

            # Update the image field
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
                    "image": request.build_absolute_uri(dish.image.url) if dish.image else None
                }
            })
            
        except Dish.DoesNotExist:
            return JsonResponse({"error": "Dish not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


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


# 👤 1️⃣ List all persons
class PersonListView(View):
    def get(self, request):
        persons = Person.objects.all().order_by('role', 'name')
        data = [
            {
                "id": p.id,
                "name": p.name,
                "role": p.get_role_display(),
                "contact": p.contact,
                "joined_date": str(p.joined_date),
            }
            for p in persons
        ]
        return JsonResponse(data, safe=False)


# 💰 2️⃣ Expense Filter 
@method_decorator(csrf_exempt, name='dispatch')
class ExpenseFilterView(View):
    def post(self, request):
        try:
            body = json.loads(request.body.decode('utf-8'))
            filter_type = body.get('filter_type')
            start_date_str = body.get('start_date')
            end_date_str = body.get('end_date')
            person_id = body.get('person_id')

            start_date, end_date = get_date_range(filter_type, start_date_str, end_date_str)
            if not start_date or not end_date:
                return JsonResponse({"error": "Invalid filter or date range."}, status=400)

            expenses = Expense.objects.filter(timestamp__date__range=(start_date, end_date))

            if person_id:
                expenses = expenses.filter(person_id=person_id)

            total_amount = sum(exp.amount for exp in expenses)

            category_summary = {}
            for exp in expenses:
                cat = exp.get_category_display()
                category_summary[cat] = category_summary.get(cat, 0) + float(exp.amount)

            data = {
                "filter_applied": filter_type or "custom_range",
                "start_date": str(start_date),
                "end_date": str(end_date),
                "total_amount": float(total_amount),
                "category_summary": category_summary,
                "expenses": [
                    {
                        "id": exp.id,
                        "timestamp": str(exp.timestamp),
                        "category": exp.get_category_display(),
                        "description": exp.description,
                        "amount": float(exp.amount),
                        "person": exp.person.name if exp.person else None,
                        "role": exp.person.get_role_display() if exp.person else None,
                    }
                    for exp in expenses
                ],
            }
            return JsonResponse(data, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
@method_decorator(csrf_exempt, name='dispatch')
class PersonCreateView(View):
    def post(self, request):
        try:
            body = json.loads(request.body.decode('utf-8'))
            name = body.get('name')
            role = body.get('role')  # 'worker' or 'manager'
            contact = body.get('contact', None)

            if not name or not role:
                return JsonResponse({"error": "Both name and role are required."}, status=400)

            person = Person.objects.create(
                name=name,
                role=role,
                contact=contact
            )

            return JsonResponse({
                "message": "Person created successfully.",
                "person": {
                    "id": person.id,
                    "name": person.name,
                    "role": person.get_role_display(),
                    "contact": person.contact,
                    "joined_date": str(person.joined_date),
                }
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# 💰 3️⃣ Create a new expense
@method_decorator(csrf_exempt, name='dispatch')
class ExpenseCreateView(View):
    def post(self, request):
        try:
            body = json.loads(request.body.decode('utf-8'))
            category = body.get('category')
            description = body.get('description',None)
            amount = body.get('amount')
            person_id = body.get('person_id')  # mandatory
            timestamp_str = body.get('timestamp')

            # ❗ Require person_id to be provided
            if not person_id:
                return JsonResponse(
                    {"error": "person_id is required to create an expense."},
                    status=400
                )

            # ✅ Check if person exists
            person = Person.objects.filter(id=person_id).first()
            if not person:
                return JsonResponse(
                    {"error": f"Person with ID {person_id} not found."},
                    status=404
                )

            # ✅ Validate remaining required fields
            if not category  or not amount:
                return JsonResponse(
                    {"error": "Category, description, and amount are required."},
                    status=400
                )

            # ✅ Parse timestamp or use now
            timestamp = timezone.now()
            if timestamp_str:
                try:
                    timestamp = timezone.datetime.fromisoformat(timestamp_str)
                except Exception:
                    pass

            # ✅ Create expense (person required)
            expense = Expense.objects.create(
                person=person,
                category=category,
                description=description,
                amount=amount,
                timestamp=timestamp
            )

            return JsonResponse({
                "message": "Expense added successfully.",
                "expense": {
                    "id": expense.id,
                    "person": expense.person.name,
                    "category": expense.get_category_display(),
                    "description": expense.description,
                    "amount": float(expense.amount),
                    "timestamp": str(expense.timestamp)
                }
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)









class AnalyticsSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Analytics summary API:
        - Default: Shows today's income, expense, and balance
        - ?filter=all → Shows all-time totals
        - ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD → Shows data for that range
        """
        filter_type = request.GET.get('filter', None)
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        # Case 1️⃣: Date Range Filter
        if start_date_str and end_date_str:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if not start_date or not end_date:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

            income = Order.objects.filter(created_at__date__range=[start_date, end_date]).aggregate(total=Sum('total_amount'))['total'] or 0
            expense = Expense.objects.filter(timestamp__date__range=[start_date, end_date]).aggregate(total=Sum('amount'))['total'] or 0
            label = f"From {start_date} to {end_date}"

        # Case 2️⃣: All-Time Data
        elif filter_type == 'all':
            income = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0
            expense = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
            label = "All-Time Data"

        # Case 3️⃣: Default → Today's Data
        else:
            today = date.today()
            income = Order.objects.filter(created_at__date=today).aggregate(total=Sum('total_amount'))['total'] or 0
            expense = Expense.objects.filter(timestamp__date=today).aggregate(total=Sum('amount'))['total'] or 0
            label = f"Today ({today})"

        balance = income - expense

        return Response({
            'label': label,
            'total_income': float(income),
            'total_expense': float(expense),
            'balance': float(balance)
        })
        
class WorkerExpenseByDateView(APIView):
    """
    Returns worker expense (wage category) for a specific date or date range.
    Supports filter types: 'today', 'all', 'custom' (with start_date and end_date).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get filter parameters
        filter_type = request.GET.get('filter', 'today')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Legacy support for single 'date' parameter
        single_date = request.GET.get('date')

        try:
            # Build queryset based on filter type
            queryset = Expense.objects.filter(category='wage')

            if single_date:
                # Legacy single date filter
                date_obj = parse_date(single_date)
                if not date_obj:
                    return Response({
                        'error': 'Invalid date format. Use YYYY-MM-DD.'
                    }, status=400)
                queryset = queryset.filter(timestamp__date=date_obj)
                date_label = str(date_obj)
                
            elif filter_type == 'all':
                # No date filtering - all time
                date_label = 'All Time'
                
            elif filter_type == 'custom' and start_date and end_date:
                # Custom date range
                start_date_obj = parse_date(start_date)
                end_date_obj = parse_date(end_date)
                
                if not start_date_obj or not end_date_obj:
                    return Response({
                        'error': 'Invalid date format. Use YYYY-MM-DD for both dates.'
                    }, status=400)
                
                if start_date_obj > end_date_obj:
                    return Response({
                        'error': 'Start date must be before or equal to end date.'
                    }, status=400)
                
                queryset = queryset.filter(
                    timestamp__date__gte=start_date_obj,
                    timestamp__date__lte=end_date_obj
                )
                date_label = f'{start_date_obj} to {end_date_obj}'
                
            else:
                # Default to today
                today = date.today()
                queryset = queryset.filter(timestamp__date=today)
                date_label = str(today)

            # Calculate total worker expense
            total_worker_expense = queryset.aggregate(
                total=Sum('amount')
            )['total'] or 0

            return Response({
                'success': True,
                'date': date_label,
                'filter_type': filter_type,
                'total_worker_expense': float(total_worker_expense)
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)
# 📈 1️⃣ Business Growth Insight — Daily Revenue Trend
class DailyRevenueTrendView(APIView):
    """
    Returns last 7 days (or ?days=N) income trend for charts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.GET.get("days", 7))
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        data = (
            Order.objects.filter(created_at__date__range=[start_date, end_date])
            .values("created_at__date")
            .annotate(daily_income=Sum("total_amount"))
            .order_by("created_at__date")
        )

        labels = [str(item["created_at__date"]) for item in data]
        income = [item["daily_income"] for item in data]

        return Response({
            "labels": labels,
            "daily_income": income
        })


# 🍽️ 2️⃣ Business Insight — Top Selling Dishes
# ==========================================
# GET TOP SELLING DISHES (DEBUGGED)
# ==========================================
class TopSellingDishesView(APIView):
    """
    Returns all dishes sold within the specified date range, ordered by total revenue.
    Filters out dishes with zero count.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get date filters from query parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            filter_type = request.query_params.get('filter', 'today')

            # Build the base queryset
            queryset = OrderItem.objects.all()

            # Apply date filters
            if filter_type == 'all':
                # No date filtering - all time data
                pass
            elif filter_type == 'custom' and start_date and end_date:
                # Custom date range
                queryset = queryset.filter(
                    order__created_at__date__gte=start_date,
                    order__created_at__date__lte=end_date
                )
            else:
                # Default to today
                from django.utils import timezone
                today = timezone.now().date()
                queryset = queryset.filter(order__created_at__date=today)

            # Aggregate dish data
            dishes_data = (
                queryset
                .values('dish__name')
                .annotate(
                    total_quantity=Sum('quantity'),
                    total_orders=Count('order', distinct=True),
                    total_revenue=Sum('price', output_field=DecimalField(max_digits=10, decimal_places=2))
                )
                .filter(total_quantity__gt=0)  # Exclude dishes with zero count
                .order_by('-total_revenue')  # Order by highest revenue first
            )

            # Format result
            result = []
            for item in dishes_data:
                result.append({
                    'dish_name': item['dish__name'],
                    'total_sold': item['total_quantity'],
                    'total_quantity': item['total_quantity'],
                    'total_orders': item['total_orders'],
                    'total_revenue': float(item['total_revenue']) if item['total_revenue'] else 0
                })

            return Response({
                "success": True,
                "dishes": result,
                "count": len(result)
            })
        
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=500)