"""increase shares.token length

Revision ID: ec3f319b0ab7
Revises: 8aacf620640a
Create Date: 2026-08-10 ...
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ec3f319b0ab7"
down_revision: Union[str, None] = "8aacf620640a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "sqlite":
        # SQLite has no ALTER COLUMN TYPE support → rebuild the table
        with op.batch_alter_table("shares", schema=None) as batch_op:
            batch_op.alter_column(
                "token",
                existing_type=sa.VARCHAR(length=100),
                type_=sa.Text(),
                existing_nullable=False,
            )
    else:
        # Postgres / other databases
        op.alter_column(
            "shares",
            "token",
            existing_type=sa.VARCHAR(length=100),
            type_=sa.Text(),
            existing_nullable=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("shares", schema=None) as batch_op:
            batch_op.alter_column(
                "token",
                existing_type=sa.Text(),
                type_=sa.VARCHAR(length=100),
                existing_nullable=False,
            )
    else:
        op.alter_column(
            "shares",
            "token",
            existing_type=sa.Text(),
            type_=sa.VARCHAR(length=100),
            existing_nullable=False,
        )
