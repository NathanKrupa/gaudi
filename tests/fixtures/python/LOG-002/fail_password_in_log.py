"""Fixture for LOG-002: logger calls referencing sensitive variable names."""

import logging

logger = logging.getLogger(__name__)


def login(username, password):
    logger.info("User %s logged in with password %s", username, password)
    api_key = lookup_key(username)
    logger.debug(f"Using api_key={api_key}")
    logger.error("Auth failed", extra={"token": "abc"})


def lookup_key(username):
    return "secret"
