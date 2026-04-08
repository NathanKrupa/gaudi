"""Fixture for ASYNC-003: module with both async def and sync requests calls."""

import requests


async def fetch_async(url):
    return url


def fetch_sync(url):
    return requests.get(url)
