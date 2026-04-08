"""Fixture for ARCH-020: a class method calling os.getenv directly."""

import os


class Client:
    def fetch(self):
        api_key = os.getenv("API_KEY")
        return api_key
