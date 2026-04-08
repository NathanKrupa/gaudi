"""Fixture for SMELL-023: subclass implements all inherited methods."""


class Handler:
    def open(self):
        return "open"

    def read(self):
        return "data"


class FileHandler(Handler):
    def open(self):
        return "file open"

    def read(self):
        return "file data"
