"""Fixture: Error swallowing — log and forget."""

import logging

logger = logging.getLogger(__name__)


def process_payment(payment):
    try:
        charge(payment)
    except Exception as e:
        logger.error(f"Payment failed: {e}")


def process_with_reraise(payment):
    try:
        charge(payment)
    except Exception as e:
        logger.error(f"Payment failed: {e}")
        raise


def charge(payment):
    pass
