"""Fixture for STAB-005: time.sleep in a sync function is out of scope."""

import time

import requests


def fetch(url):
    time.sleep(1)
    return requests.get(url)
