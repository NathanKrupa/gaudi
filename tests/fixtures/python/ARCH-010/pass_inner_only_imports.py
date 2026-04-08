"""Fixture for ARCH-010: imports from inner-layer modules only."""

from services.orders import process
from connectors.db import get_connection


def use():
    return (process, get_connection)
