"""Fixture for SMELL-009: method primarily accesses self."""


class Order:
    def __init__(self):
        self.id = 1
        self.subtotal = 0
        self.tax = 0
        self.shipping = 0
        self.discount = 0

    def total(self, customer):
        rate = customer.tax_rate
        return self.subtotal + self.tax * rate + self.shipping - self.discount
