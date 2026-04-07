"""Fixture for ERR-001: a broad handler is acceptable when it re-raises."""

import logging

logger = logging.getLogger(__name__)


def run(work):
    try:
        return work()
    except Exception:
        logger.exception("work failed")
        raise
