from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator
from django.forms.models import model_to_dict
from .models import *
import json
from django.db.models import Sum, Count, F
from django.utils.dateparse import parse_datetime,parse_date
from .print_utils import print_order_bill 
from django.utils import timezone
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

class DishListView(View):
    def get(self, request):
        dishes = Dish.objects.all()
        data = []

        for dish in dishes:
            data.append({
                'id': dish.id,
                'name': dish.name,
                'price': float(dish.price),
                'image': request.build_absolute_uri(dish.image.url) if dish.image else None
            })

        return JsonResponse(data, safe=False)

class DishDetailView(View):
    def get(self, request, dish_id):
        try:
            dish = Dish.objects.get(id=dish_id)
            data = {
                "id": dish.id,
                "name": dish.name,
                "price": float(dish.price),
                # Convert image field to URL if exists
                "image": request.build_absolute_uri(dish.image.url) if dish.image else None
            }
            return JsonResponse(data)
        except Dish.DoesNotExist:
            return JsonResponse({"error": "Dish not found"}, status=404)
# ✅ CREATE Order (with order_type)
@method_decorator(csrf_exempt, name='dispatch')
class CreateOrderView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            items_data = data.get('items', [])
            frontend_total = float(data.get('total_amount', 0))
            order_type = data.get('order_type', 'dine_in')

            order = Order.objects.create(total_amount=0, order_type=order_type)
            backend_total = 0

            for item in items_data:
                dish_id = item.get('dish_id')
                quantity = int(item.get('quantity', 1))

                dish = Dish.objects.get(id=dish_id)
                price = dish.price * quantity
                backend_total += price

                OrderItem.objects.create(
                    order=order,
                    dish=dish,
                    quantity=quantity,
                    price=price
                )

            if frontend_total != float(backend_total):
                order.delete()
                return JsonResponse({
                    "error": f"Total mismatch! Frontend sent {frontend_total}, backend calculated {backend_total}"
                }, status=400)

            order.total_amount = backend_total
            order.save()

            # ✅ Print the order bill
            try:
                print_order_bill(order)
            except Exception as e:
                print("⚠️ Printing failed:", e)

            order_data = {
                "id": order.id,
                "order_type": order.get_order_type_display(),
                "created_at": order.created_at,
                "total_amount": order.total_amount,
                "items": [
                    {
                        "dish_name": item.dish.name,
                        "quantity": item.quantity,
                        "price": float(item.price)
                    }
                    for item in order.items.all()
                ]
            }

            return JsonResponse({
                "message": "Order created successfully & bill printed!",
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


# views.py - Add this new view for creating dishes
@method_decorator(csrf_exempt, name='dispatch')
class CreateDishView(View):
    def post(self, request):
        try:
            # For multipart/form-data, use request.POST and request.FILES
            name = request.POST.get('name')
            price = request.POST.get('price')
            image = request.FILES.get('image')  # Get uploaded image file
            
            if not name or not price:
                return JsonResponse({
                    "error": "Name and price are required"
                }, status=400)
            
            # Create new dish
            dish = Dish.objects.create(
                name=name,
                price=price,
                image=image  # This will be saved in media/dishes/
            )
            
            return JsonResponse({
                "message": "Dish created successfully!",
                "dish": {
                    "id": dish.id,
                    "name": dish.name,
                    "price": float(dish.price),
                    "image": request.build_absolute_uri(dish.image.url) if dish.image else None
                }
            }, status=201)
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
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













# 2️⃣ Top 5 selling dishes (by quantity)
def top_selling_dishes(request):
    top_dishes = (
        OrderItem.objects
        .values('dish__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:5]
    )
    return JsonResponse({'top_selling_dishes': list(top_dishes)})


# 3️⃣ Total revenue per day
def daily_revenue(request):
    revenue_data = (
        Order.objects
        .values('created_at__date')
        .annotate(total_revenue=Sum('total_amount'))
        .order_by('created_at__date')
    )
    return JsonResponse({'daily_revenue': list(revenue_data)})


# 4️⃣ Average order value
def avg_order_value(request):
    avg_value = Order.objects.aggregate(avg_value=Sum('total_amount') / Count('id'))['avg_value'] or 0
    return JsonResponse({'average_order_value': round(avg_value, 2)})


# 5️⃣ Order type distribution (Delivery vs Dine In)
def order_type_distribution(request):
    dist = (
        Order.objects
        .values('order_type')
        .annotate(count=Count('id'))
    )
    return JsonResponse({'order_type_distribution': list(dist)})


# 6️⃣ Top revenue-generating dishes
def top_revenue_dishes(request):
    top_revenue = (
        OrderItem.objects
        .values('dish__name')
        .annotate(total_revenue=Sum('price'))
        .order_by('-total_revenue')[:5]
    )
    return JsonResponse({'top_revenue_dishes': list(top_revenue)})
