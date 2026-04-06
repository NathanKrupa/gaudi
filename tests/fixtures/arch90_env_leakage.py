"""Fixture: os.getenv() in class methods instead of factory."""

import os


class DatabaseService:
    def connect(self):
        host = os.getenv("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        return f"{host}:{port}"

    def get_timeout(self):
        return int(os.getenv("DB_TIMEOUT", "30"))


def create_service():
    """This is fine — factory function reading env."""
    host = os.getenv("DB_HOST", "localhost")
    return DatabaseService()
