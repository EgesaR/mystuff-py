"""updated the feedback table.

Revision ID: 092d90292a93
Revises: 1a5a29bd0d8d
Create Date: 2026-09-14 00:23:49.935337
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "092d90292a93"
down_revision: str | None = "1a5a29bd0d8d"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade the feedback table."""
    op.add_column(
        "feedback",
        sa.Column(
            "rating",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade the feedback table."""
    op.drop_column(
        "feedback",
        "rating",
    )
