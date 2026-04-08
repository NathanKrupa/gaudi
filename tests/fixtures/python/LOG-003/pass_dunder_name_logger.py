"""Fixture for LOG-003: getLogger uses __name__ (or no arg)."""

import logging

logger = logging.getLogger(__name__)
root_logger = logging.getLogger()
