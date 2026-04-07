"""Fixture for CELERY-SCALE-001: a plain function in a celery-aware module is out of scope."""

from celery import shared_task


def send_invoice(order_id):
    return order_id


_ = shared_task  # silence unused import
