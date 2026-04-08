"""Fixture for STAB-008: external call wrapped in try/except with fallback."""

import requests


def get_user(user_id):
    try:
        response = requests.get(f"https://api.example.com/users/{user_id}")
        return response.json()
    except requests.RequestException:
        return {"id": user_id, "name": "unknown"}
