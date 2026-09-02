"""Fixture for ERR-003: the swallow is the defect, whatever level it logs at.

Canary for the estate incident this rule missed (grantspider 7461aa6a): an
unreadable object-store read was logged at warning, treated as "the site says
nothing", and stamped 30-day empty sentinels across an outage. 127 of that
repo's 144 swallows log at warning; the rule saw only the 17 at error.
"""

import logging

logger = logging.getLogger(__name__)


def fetch(store, key):
    try:
        return store.read(key)
    except OSError:
        logger.warning("could not read %s", key)
        return None
