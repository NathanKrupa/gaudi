"""Fixture for SVC-002: a single aggregate call replaces the chatty trio."""

import requests


def fetch_dashboard(user_id):
    return requests.get(f"https://api.example.com/dashboard?user={user_id}")
