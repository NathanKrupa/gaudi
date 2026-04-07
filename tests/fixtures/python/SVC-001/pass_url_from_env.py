"""Fixture for SVC-001: service URLs resolved from configuration."""

import os

API_URL = os.environ["API_URL"]
WORKER_URL = os.environ["WORKER_URL"]


def call():
    return (API_URL, WORKER_URL)
