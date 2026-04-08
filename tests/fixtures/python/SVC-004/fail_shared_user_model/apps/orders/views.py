"""Orders app reaches across the boundary into users.models."""

from apps.users.models import User


def list_orders_for(user_id):
    return User.objects.filter(pk=user_id)
