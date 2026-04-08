"""Fixture for SVC-005: multiple calls to the same upstream service are not a chain."""

import requests


def fetch_user_bundle(user_id):
    profile = requests.get(f"https://api.example.com/users/{user_id}")
    settings = requests.get(f"https://api.example.com/users/{user_id}/settings")
    return profile.json(), settings.json()
