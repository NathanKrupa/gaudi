"""Fixture for LOG-001: %-formatted logger calls let logging skip work when disabled."""

import logging

logger = logging.getLogger(__name__)


def process_order(order_id, user):
    logger.info("Processing order %s for user %s", order_id, user)
    logger.warning("Order %s has issues", order_id)
    logger.debug("Debug: %s", order_id)
    logger.error("Failed to process order %s", order_id)
