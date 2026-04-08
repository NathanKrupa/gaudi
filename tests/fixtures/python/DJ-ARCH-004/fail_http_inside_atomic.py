"""Fixture for DJ-ARCH-004: HTTP call inside @transaction.atomic."""

from django.db import transaction
import requests


@transaction.atomic
def place_order(order):
    order.status = "paid"
    order.save()
    requests.post("https://payments.example.com/charge", json={"id": order.id})
