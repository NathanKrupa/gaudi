"""Fixture for SMELL-003: a function exactly 30 lines long is at the boundary."""


def boundary(order):
    total = 0
    total += order.subtotal
    total += order.tax
    total += order.shipping
    total -= order.discount
    if order.is_member:
        total *= 0.9
    if order.is_holiday:
        total *= 0.95
    if order.use_points:
        total -= order.points
    if total < 0:
        total = 0
    order.total = total
    order.status = "priced"
    order.priced_at = "now"
    order.audit_trail.append("priced")
    order.audit_trail.append("checked")
    order.audit_trail.append("logged")
    order.audit_trail.append("notified")
    order.audit_trail.append("done")
    order.audit_trail.append("emailed")
    order.audit_trail.append("queued")
    order.audit_trail.append("archived")
    order.audit_trail.append("confirmed")
    order.notify()
    order.flush()
    return total
