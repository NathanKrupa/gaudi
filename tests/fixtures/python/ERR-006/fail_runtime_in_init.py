"""Fixture for ERR-006: __init__ raising RuntimeError leaves a partially constructed object."""


class Service:
    def __init__(self, client):
        self.client = client
        if not client.ready():
            raise RuntimeError("client not ready")
