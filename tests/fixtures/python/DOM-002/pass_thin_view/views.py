# Fixture for DOM-002: a thin view that delegates to a service must NOT trigger.
from django.http import JsonResponse

from myapp.services import order_status_label


def order_status(request, order):
    return JsonResponse({"label": order_status_label(order)})
