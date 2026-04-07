"""Fixture for ALM-ARCH-001: ordinary alembic-importing module that is not a migration.

The file imports alembic so the library is detected, but it has no module-level
``revision`` assignment, so the rule should ignore it entirely.
"""

from alembic import op


def helper() -> None:
    op.execute("SELECT 1")
