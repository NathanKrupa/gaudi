# Fixture for DOM-002: WrongLayerPlacement.
# Django view with a 5-branch if/elif chain — business logic in the outer layer.
from django.http import JsonResponse


def order_status(request, order):
    if order.status == "draft":
        label = "Not yet sent"
    elif order.status == "sent":
        label = "Awaiting payment"
    elif order.status == "paid":
        label = "Paid"
    elif order.status == "shipped":
        label = "Shipped"
    elif order.status == "delivered":
        label = "Delivered"
    else:
        label = "Unknown"
    return JsonResponse({"label": label})
