"""Fixture for ERR-003: log and re-raise -- the canonical pattern."""

import logging

logger = logging.getLogger(__name__)


def process(item):
    try:
        return item.do_work()
    except RuntimeError:
        logger.exception("work failed for %s", item)
        raise
