"""Only one app crosses into users.models -- this is allowed."""

from apps.users.models import User


def list_orders_for(user_id):
    return User.objects.filter(pk=user_id)
