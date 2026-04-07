"""Fixture for LOG-001: plain (non-f) string literals are fine."""

import logging

logger = logging.getLogger(__name__)


def heartbeat():
    logger.info("heartbeat")
    logger.warning("queue draining")
