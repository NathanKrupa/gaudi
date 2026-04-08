"""Fixture for LOG-005: endpoint logger call has no correlation id in extra."""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/users")
def list_users():
    logger.info("Listing users")
    return []
