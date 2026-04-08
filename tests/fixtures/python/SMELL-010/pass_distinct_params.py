"""Fixture for SMELL-010: each function has its own parameter set."""


def create_user(name, email, age):
    return (name, email, age)


def create_order(product, quantity, price):
    return (product, quantity, price)


def create_invoice(customer, total, due_date):
    return (customer, total, due_date)
