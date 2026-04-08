"""Fixture for SVC-005: synchronous chain across three distinct services."""

import requests


def render_order_page(order_id):
    order = requests.get(f"https://orders.example.com/api/{order_id}")
    user = requests.get(f"https://users.example.com/api/{order.json()['user_id']}")
    inventory = requests.post(
        "https://inventory.example.com/api/reserve",
        json={"order_id": order_id},
    )
    return order, user, inventory
