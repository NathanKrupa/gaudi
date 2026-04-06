"""Fixture: Duplicated Code."""


def process_users(users):
    result = []
    for user in users:
        if user.active:
            name = user.first_name + " " + user.last_name
            result.append({"name": name, "email": user.email})
    return result


def process_customers(customers):
    result = []
    for customer in customers:
        if customer.active:
            name = customer.first_name + " " + customer.last_name
            result.append({"name": name, "email": customer.email})
    return result


def process_orders(orders):
    return [o for o in orders if o.total > 0]
