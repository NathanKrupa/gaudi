"""Fixture for SMELL-003: a 26-line function trips the > 25 threshold."""


def process_order(order):
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
    order.notify()
    order.flush()
    return total
