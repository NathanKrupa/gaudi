"""Fixture for ALM-ARCH-001: alembic migration with a real downgrade body."""

from alembic import op
import sqlalchemy as sa

revision = "abc123"
down_revision = "def456"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=255)))


def downgrade() -> None:
    op.drop_column("users", "email")
