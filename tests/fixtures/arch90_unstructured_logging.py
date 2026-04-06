"""Fixture: Unstructured logging with f-strings."""

import logging

logger = logging.getLogger(__name__)


def process_order(order_id, user):
    logger.info(f"Processing order {order_id} for user {user}")
    logger.warning(f"Order {order_id} has issues")
    logger.debug(f"Debug: {order_id}")


def good_logging(order_id, user):
    logger.info("Processing order %s for user %s", order_id, user)
