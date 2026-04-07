"""Fixture for SVC-002: a function making three sequential HTTP calls."""

import requests


def fetch_dashboard(user_id):
    user = requests.get(f"https://api.example.com/users/{user_id}")
    orders = requests.get(f"https://api.example.com/orders?user={user_id}")
    invoices = requests.get(f"https://api.example.com/invoices?user={user_id}")
    return (user, orders, invoices)
