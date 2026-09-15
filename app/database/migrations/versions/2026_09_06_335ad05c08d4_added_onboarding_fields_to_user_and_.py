"""Added onboarding fields to user and table.

Revision ID: 335ad05c08d4
Revises: f193caedc82e
Create Date: 2026-09-06 14:59:52.389638
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "335ad05c08d4"
down_revision: Union[str, Sequence[str], None] = "f193caedc82e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create onboarding-related tables."""

    op.create_table(
        "user_onboarding",
        sa.Column(
            "user_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "skipped",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "current_step",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            name="uq_user_onboarding_user",
        ),
    )

    op.create_index(
        "ix_user_onboarding_user_id",
        "user_onboarding",
        ["user_id"],
        unique=True,
    )

    op.create_table(
        "beta_signups",
        sa.Column(
            "user_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "interested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "status",
            sa.String(length=24),
            nullable=False,
            server_default="not_interested",
        ),
        sa.Column(
            "signed_up_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            name="uq_beta_signups_user",
        ),
    )

    op.create_index(
        "ix_beta_signups_user_id",
        "beta_signups",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    """Remove onboarding-related tables."""

    op.drop_index(
        "ix_beta_signups_user_id",
        table_name="beta_signups",
    )

    op.drop_table("beta_signups")

    op.drop_index(
        "ix_user_onboarding_user_id",
        table_name="user_onboarding",
    )

    op.drop_table("user_onboarding")
