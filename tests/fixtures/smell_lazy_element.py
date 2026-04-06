"""Fixture: Lazy Element."""


class UserValidator:
    def validate(self, user):
        return len(user.name) > 0


class OrderProxy:
    def __init__(self, order):
        self._order = order

    def get_total(self):
        return self._order.get_total()


class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b
