"""Linear chain head 2 -- builds on top of 001 (no shared parent with anything else)."""

from alembic import op
import sqlalchemy as sa

revision = "ccc333"
down_revision = "aaa111"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("age", sa.Integer()))


def downgrade() -> None:
    op.drop_column("users", "age")
