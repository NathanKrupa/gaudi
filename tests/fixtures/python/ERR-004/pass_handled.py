"""Fixture for ERR-004: handler does real work, not pass."""

import logging

logger = logging.getLogger(__name__)


def fetch(client, key):
    try:
        return client.get(key)
    except ValueError:
        logger.warning("bad key %s", key)
        return None
