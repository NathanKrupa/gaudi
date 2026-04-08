"""Fixture for SVC-005: synchronous chain calling two distinct services."""

import requests


def fetch_user_dashboard(user_id):
    profile = requests.get(f"https://users.example.com/api/{user_id}")
    invoices = requests.get(f"https://billing.example.com/api/{user_id}")
    return profile.json(), invoices.json()
