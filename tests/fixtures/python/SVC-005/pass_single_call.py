"""Fixture for SVC-005: a function with a single outbound call is fine."""

import requests


def fetch_profile(user_id):
    return requests.get(f"https://users.example.com/api/{user_id}").json()
