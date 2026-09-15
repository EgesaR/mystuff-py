"""Added onboarding table and attribute.

Revision ID: 8d9824ae545e
Revises: 335ad05c08d4
Create Date: 2026-09-08 01:44:23.147916
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8d9824ae545e"
down_revision: str | Sequence[str] | None = "335ad05c08d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------
    # SQLite-safe migration of user_onboarding.current_step
    #
    # Previous:
    #     INTEGER
    #
    # New:
    #     VARCHAR(32)
    #
    # Existing integer values are converted explicitly to the
    # application's onboarding step names.
    # ------------------------------------------------------------------

    with op.batch_alter_table("user_onboarding", schema=None) as batch_op:
        batch_op.alter_column(
            "current_step",
            existing_type=sa.Integer(),
            type_=sa.String(length=32),
            existing_nullable=False,
            existing_server_default=sa.text("0"),
        )

    # The column is now textual, so safely convert existing values.
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            UPDATE user_onboarding
            SET current_step = CASE
                WHEN current_step = '0' THEN 'welcome'
                WHEN current_step = '1' THEN 'workspace'
                WHEN current_step = '2' THEN 'features'
                WHEN current_step = '3' THEN 'feedback'
                WHEN current_step = '4' THEN 'beta'
                WHEN current_step = '5' THEN 'complete'
                WHEN current_step IS NULL THEN 'welcome'
                ELSE current_step
            END
            """
        )
    )

    # Change the default from the old integer value to the first
    # onboarding step.
    with op.batch_alter_table("user_onboarding", schema=None) as batch_op:
        batch_op.alter_column(
            "current_step",
            existing_type=sa.String(length=32),
            type_=sa.String(length=32),
            existing_nullable=False,
            existing_server_default=sa.text("0"),
            server_default=sa.text("'welcome'"),
        )

        # The model revision removed the unique constraint on user_id.
        batch_op.drop_constraint(
            "uq_user_onboarding_user",
            type_="unique",
        )


def downgrade() -> None:
    """Downgrade schema."""

    connection = op.get_bind()

    # ------------------------------------------------------------------
    # Convert onboarding step names back to the legacy integer values
    # before changing the column back to INTEGER.
    # ------------------------------------------------------------------

    connection.execute(
        sa.text(
            """
            UPDATE user_onboarding
            SET current_step = CASE
                WHEN current_step = 'welcome' THEN '0'
                WHEN current_step = 'workspace' THEN '1'
                WHEN current_step = 'features' THEN '2'
                WHEN current_step = 'feedback' THEN '3'
                WHEN current_step = 'beta' THEN '4'
                WHEN current_step = 'complete' THEN '5'
                ELSE '0'
            END
            """
        )
    )

    with op.batch_alter_table("user_onboarding", schema=None) as batch_op:
        batch_op.alter_column(
            "current_step",
            existing_type=sa.String(length=32),
            type_=sa.Integer(),
            existing_nullable=False,
            existing_server_default=sa.text("'welcome'"),
            server_default=sa.text("0"),
        )

        # Restore the original uniqueness rule.
        batch_op.create_unique_constraint(
            "uq_user_onboarding_user",
            ["user_id"],
        )