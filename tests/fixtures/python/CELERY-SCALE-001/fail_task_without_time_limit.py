"""Fixture for CELERY-SCALE-001: a Celery task without time_limit/soft_time_limit."""

from celery import shared_task


@shared_task(autoretry_for=(Exception,), max_retries=3)
def send_invoice(order_id):
    return order_id
