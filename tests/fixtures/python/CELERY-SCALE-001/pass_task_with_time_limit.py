"""Fixture for CELERY-SCALE-001: task is bounded by a time limit."""

from celery import shared_task


@shared_task(time_limit=60, soft_time_limit=50)
def send_invoice(order_id):
    return order_id
