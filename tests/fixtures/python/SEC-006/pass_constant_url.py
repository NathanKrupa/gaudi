"""Fixture for SEC-006: constant URLs are not tainted."""
import requests
import httpx


def fetch_api():
    return requests.get("https://api.example.com/data")


def fetch_httpx_constant():
    url = "https://internal.example.com/health"
    return httpx.get(url)


def fetch_with_constant_base(item_id):
    url = f"https://api.example.com/items/{item_id}"
    return requests.get(url)
