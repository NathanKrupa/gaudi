"""Linear chain head 1 -- followed by 002 which has down_revision='aaa111'."""

from alembic import op
import sqlalchemy as sa

revision = "aaa111"
down_revision = "root00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=255)))


def downgrade() -> None:
    op.drop_column("users", "email")
