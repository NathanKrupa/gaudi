"""Fixture for ERR-003: warning-level logging followed by a re-raise is fine.

The rule keys on the swallow, not the level -- so widening the levels must not
make the canonical log-and-re-raise pattern fire.
"""

import logging

logger = logging.getLogger(__name__)


def fetch(store, key):
    try:
        return store.read(key)
    except OSError:
        logger.warning("could not read %s", key)
        raise
