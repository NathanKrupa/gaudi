"""Fixture for SVC-002: two HTTP calls is below the chatty threshold (>= 3)."""

import requests


def fetch_user_and_orders(user_id):
    user = requests.get(f"https://api.example.com/users/{user_id}")
    orders = requests.get(f"https://api.example.com/orders?user={user_id}")
    return (user, orders)
