"""Fixture for SMELL-009: method touches customer attrs more than self."""


class Order:
    def __init__(self):
        self.id = 1

    def get_customer_summary(self, customer):
        name = customer.name
        email = customer.email
        phone = customer.phone
        address = customer.address
        return (name, email, phone, address)
