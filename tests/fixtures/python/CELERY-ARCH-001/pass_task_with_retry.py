"""Fixture for CELERY-ARCH-001: task declares its retry policy."""

from celery import shared_task


@shared_task(autoretry_for=(Exception,), max_retries=3, retry_backoff=True)
def send_invoice(order_id):
    return order_id
