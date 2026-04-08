"""Fixture for SMELL-015: function with 2 unused None-default params."""


def fetch(url, headers=None, timeout=None):
    return url
