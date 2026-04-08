"""Billing app also reaches across the boundary into users.models."""

from apps.users.models import User


def invoices_for(user_id):
    user = User.objects.get(pk=user_id)
    return user
