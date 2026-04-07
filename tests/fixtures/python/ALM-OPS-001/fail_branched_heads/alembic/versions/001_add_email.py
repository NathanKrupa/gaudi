"""Branch A: shares down_revision='root00' with branch B -- this is the divergence."""

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
