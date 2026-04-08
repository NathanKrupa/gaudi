"""Fixture for DJ-ARCH-004: external HTTP happens outside the atomic block."""

from django.db import transaction
import requests


def place_order(order):
    with transaction.atomic():
        order.status = "paid"
        order.save()
    requests.post("https://payments.example.com/charge", json={"id": order.id})
