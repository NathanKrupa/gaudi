"""Fixture: Magic strings — repeated string literals."""


def process(order):
    if order.status == "pending":
        return handle_pending(order)
    return None


def validate(order):
    if order.status == "pending":
        return True
    return False


def notify(order):
    if order.status == "pending":
        send_notification(order)


def handle_pending(order):
    pass


def send_notification(order):
    pass
