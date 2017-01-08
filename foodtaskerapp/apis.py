import json

from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from oauth2_provider.models import AccessToken

from foodtaskerapp.models import Restaurant, Meal, Order, OrderDetails
from foodtaskerapp.serializers import RestaurantSerializer, MealSerializer, OrderSerializer

def customer_get_restaurants(request):
	restaurants = RestaurantSerializer(
		Restaurant.objects.all().order_by("-id"),
		many = True,
		context = {"request": request}
	).data

	return JsonResponse({"restaurants":restaurants})


def customer_get_meals(request, restaurant_id):
	meals = MealSerializer(
		Meal.objects.filter(restaurant_id = restaurant_id).order_by("-id"),
		many = True,
		context = {"request": request}
	).data
	return JsonResponse({"meals": meals})

@csrf_exempt	
def customer_add_order(request):
	"""
		params:
			access_token
			restaurant_id
			address
			order_details (json format), example:
				[{"meals_id":1, "quantity": 2},{"meals_id":2, "quantity": 3}]
			stripe_token

		return:
		{"status": "success"}
	"""

	if request.method == "POST":
		# Get token
		access_token = AccessToken.objects.get(token = request.POST.get("access_token"),
			expires__gt = timezone.now())

		# Get profile
		customer = access_token.user.customer

		#Check whtether customer has any order that is not delivered 
		if Order.objects.filter(customer = customer).exclude(status = Order.DELIVERED):
			return JsonResponse({"status": "fail", "error": "Your last order must be completed."})

		# Check Address
		if not request.POST["address"]:
			return JsonResponse({"status": "fail", "error": "Address is required."})

		# Get Order Details
		order_details = json.loads(request.POST["order_details"])

		order_total = 0
		for meal in order_details:
			 order_total += Meal.objects.get(id = meal["meal_id"]).price * meal["quantity"]


		if len(order_details) > 0:
			# Step 1 - Create an Order

			order = Order.objects.create(
				customer = customer,
				restaurant_id = request.POST['restaurant_id'],
				total = order_total,
				status = Order.COOKING,
				address = request.POST["address"]
			)

			# Step 2 - Create Order details
			for meal in order_details:
				OrderDetails.objects.create(
					order = order,
					meal_id = meal["meal_id"],
					quantity = meal['quantity'],
					sub_total = Meal.objects.get(id = meal["meal_id"]).price * meal["quantity"]
				)
			return JsonResponse({"status": "success"})

def customer_get_latest_order(request):
	access_token = AccessToken.objects.get(token = request.GET.get("access_token"), 
		expires__gt = timezone.now())

	customer = access_token.user.customer
	order = OrderSerializer(Order.objects.filter(customer = customer).last()).data

	return JsonResponse({"order": order})


def restaurant_order_notification(request, last_request_time):
	notification = Order.objects.filter(restaurant = request.user.restaurant, 
		created_at__gt = last_request_time).count()

	return JsonResponse({"notification": notification})

