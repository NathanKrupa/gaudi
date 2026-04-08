"""Fixture for SMELL-019: method asks the other object to mutate itself."""


class OrderProcessor:
    def finalize(self, order):
        order.mark_complete()
        return order
