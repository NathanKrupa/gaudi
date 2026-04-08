"""Fixture for LOG-004: print() calls in a service module that has no CLI imports."""


def process_order(order_id):
    print(f"Processing order {order_id}")
    print("Done")
    return order_id
