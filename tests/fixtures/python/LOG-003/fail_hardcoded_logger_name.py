"""Fixture for LOG-003: getLogger called with a hardcoded string."""

import logging

logger = logging.getLogger("myapp.views")
audit_logger = logging.getLogger("audit")
