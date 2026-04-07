# Fixture for DOM-002 boundary: 4 branches is exactly above the threshold.
from django.http import JsonResponse


def role_label(request, user):
    if user.role == "admin":
        label = "Admin"
    elif user.role == "staff":
        label = "Staff"
    elif user.role == "member":
        label = "Member"
    elif user.role == "guest":
        label = "Guest"
    else:
        label = "Unknown"
    return JsonResponse({"label": label})
