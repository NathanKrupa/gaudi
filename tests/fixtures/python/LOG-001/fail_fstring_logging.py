"""Fixture for LOG-001: f-strings in logger calls block lazy %-formatting."""

import logging

logger = logging.getLogger(__name__)


def process_order(order_id, user):
    logger.info(f"Processing order {order_id} for user {user}")
    logger.warning(f"Order {order_id} has issues")
    logger.debug(f"Debug: {order_id}")
    logger.error(f"Failed to process order {order_id}")
