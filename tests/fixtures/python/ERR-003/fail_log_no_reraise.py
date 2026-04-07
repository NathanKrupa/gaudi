"""Fixture for ERR-003: error logged but never re-raised (silent failure)."""

import logging

logger = logging.getLogger(__name__)


def process(item):
    try:
        return item.do_work()
    except RuntimeError:
        logger.error("work failed for %s", item)
        return None
