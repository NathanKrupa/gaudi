"""Fixture for SMELL-019: method writes 3 attributes of another object."""


class OrderProcessor:
    def finalize(self, order):
        order.status = "complete"
        order.finalized_at = "now"
        order.total = order.subtotal + order.tax
