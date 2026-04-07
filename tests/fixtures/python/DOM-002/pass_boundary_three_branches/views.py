# Fixture for DOM-002 boundary: 3 branches is below the threshold, must NOT trigger.
from django.http import JsonResponse


def status_label(request, order):
    if order.status == "draft":
        label = "Draft"
    elif order.status == "sent":
        label = "Sent"
    else:
        label = "Done"
    return JsonResponse({"label": label})
