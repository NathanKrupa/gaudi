"""Fixture for ARCH-020: configuration is injected via __init__ instead of read inside methods."""


class Client:
    def __init__(self, api_key):
        self.api_key = api_key

    def fetch(self):
        return self.api_key
