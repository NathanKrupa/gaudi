"""Fixture for SEC-006: tainted URL flows through local variable assignment."""
import requests
import urllib.request


def fetch_indirect(user_url):
    target = user_url
    return requests.get(target)


def fetch_urllib(addr):
    url = addr
    return urllib.request.urlopen(url)
