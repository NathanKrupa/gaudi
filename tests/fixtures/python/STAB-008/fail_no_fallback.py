"""Fixture for STAB-008: external HTTP call with no try/except fallback."""

import requests


def get_user(user_id):
    response = requests.get(f"https://api.example.com/users/{user_id}")
    return response.json()
