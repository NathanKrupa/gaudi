"""Fixture for ERR-006: bare `raise` inside __init__ propagates whatever happened to be active."""


class Loader:
    def __init__(self, path):
        try:
            self.fh = open(path)
        except OSError:
            raise
