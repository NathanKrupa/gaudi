"""Fixture for PY314-004: finally block does cleanup only -- no control flow statements."""

import logging

logger = logging.getLogger(__name__)


def lookup():
    try:
        return 1
    finally:
        logger.info("done")
