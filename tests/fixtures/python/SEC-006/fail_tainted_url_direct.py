"""Fixture for SEC-006: user input flows directly into HTTP calls."""
import requests
import httpx


def fetch_resource(url):
    return requests.get(url)


def fetch_with_httpx(endpoint):
    return httpx.get(endpoint)


def post_data(url, payload):
    return requests.post(url, json=payload)
