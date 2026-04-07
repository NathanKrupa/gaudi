"""Fixture for SVC-001: external public URLs are not flagged (rule keys on localhost only)."""

API_URL = "https://api.example.com/v1"


def call():
    return API_URL
