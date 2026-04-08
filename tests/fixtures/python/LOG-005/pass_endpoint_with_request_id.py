"""Fixture for LOG-005: endpoint logger call carries request_id in extra."""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/users")
def list_users(request_id: str):
    logger.info("Listing users", extra={"request_id": request_id})
    return []
