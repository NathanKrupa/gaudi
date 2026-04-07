"""Fixture for CELERY-ARCH-001: a Celery task without retry configuration."""

from celery import shared_task


@shared_task
def send_invoice(order_id):
    return order_id
