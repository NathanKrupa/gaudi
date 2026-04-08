"""Fixture for SMELL-023: subclass refuses 2 of 3 inherited methods."""


class Handler:
    def open(self):
        return "open"

    def read(self):
        return "data"

    def write(self, data):
        return data


class LimitedHandler(Handler):
    def open(self):
        return "limited"

    def read(self):
        raise NotImplementedError

    def write(self, data):
        raise NotImplementedError
