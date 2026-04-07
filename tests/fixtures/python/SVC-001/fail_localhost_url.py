"""Fixture for SVC-001: hardcoded localhost service URLs."""

API_URL = "http://localhost:8000/api"
WORKER_URL = "http://127.0.0.1:9000"


def call():
    return (API_URL, WORKER_URL)
