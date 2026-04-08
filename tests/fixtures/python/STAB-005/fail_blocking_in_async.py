"""Fixture for STAB-005: blocking time.sleep and requests.get inside an async function."""

import time

import requests


async def fetch(url):
    time.sleep(1)
    return requests.get(url)
