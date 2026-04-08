"""Fixture for ERR-006: TypeError on bad-type arguments is also conventional."""


class Wrapper:
    def __init__(self, value):
        if not isinstance(value, int):
            raise TypeError("value must be int")
        self.value = value
