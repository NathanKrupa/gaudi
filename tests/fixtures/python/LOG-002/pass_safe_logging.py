"""Fixture for LOG-002: logger calls that reference no sensitive names."""

import logging

logger = logging.getLogger(__name__)


def login(username):
    logger.info("User %s logged in", username)
    logger.debug("Login complete")
    logger.error("Auth failed", extra={"user": username})
