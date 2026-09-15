from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

"""Add admin role and pre-registration tracking.

Revision ID: 1a5a29bd0d8d
Revises: e1ed6b1f6e12
Create Date: 2026-09-13 23:45:19.890247
"""


revision: str = "1a5a29bd0d8d"
down_revision: str | Sequence[str] | None = "e1ed6b1f6e12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # --------------------------------------------------------------
    # users.is_admin
    # --------------------------------------------------------------

    user_columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    if "is_admin" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    # --------------------------------------------------------------
    # pre_registrations
    #
    # The table does not exist in the current database, so create the
    # complete table here rather than attempting ALTER TABLE on SQLite.
    # --------------------------------------------------------------

    if not inspector.has_table("pre_registrations"):
        op.create_table(
            "pre_registrations",

            # Identity
            sa.Column(
                "id",
                sa.String(length=36),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "email",
                sa.String(length=320),
                nullable=False,
            ),
            sa.Column(
                "name",
                sa.String(length=100),
                nullable=True,
            ),

            # Double opt-in verification
            sa.Column(
                "verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "verified_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "verification_token_hash",
                sa.String(length=128),
                nullable=True,
            ),
            sa.Column(
                "verification_expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),

            # Subscription
            sa.Column(
                "subscribed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "unsubscribed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "unsubscribe_token_hash",
                sa.String(length=128),
                nullable=True,
            ),

            # Campaign tracking
            sa.Column(
                "launch_email_sent_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "last_email_error",
                sa.Text(),
                nullable=True,
            ),

            # Account conversion tracking
            sa.Column(
                "converted_user_id",
                sa.String(length=36),
                sa.ForeignKey(
                    "users.id",
                    ondelete="SET NULL",
                ),
                nullable=True,
            ),
            sa.Column(
                "converted_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),

            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),

            sa.UniqueConstraint(
                "email",
                name="uq_pre_registrations_email",
            ),
            sa.UniqueConstraint(
                "unsubscribe_token_hash",
                name="uq_pre_registrations_unsubscribe_token_hash",
            ),
        )

        op.create_index(
            "ix_pre_registrations_email",
            "pre_registrations",
            ["email"],
            unique=False,
        )

        op.create_index(
            "ix_pre_registrations_converted_user_id",
            "pre_registrations",
            ["converted_user_id"],
            unique=False,
        )

        op.create_index(
            "ix_pre_registrations_verified_subscribed",
            "pre_registrations",
            ["verified", "subscribed"],
            unique=False,
        )

        op.create_index(
            "ix_pre_registrations_created_at",
            "pre_registrations",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("pre_registrations"):
        op.drop_index(
            "ix_pre_registrations_created_at",
            table_name="pre_registrations",
        )

        op.drop_index(
            "ix_pre_registrations_verified_subscribed",
            table_name="pre_registrations",
        )

        op.drop_index(
            "ix_pre_registrations_converted_user_id",
            table_name="pre_registrations",
        )

        op.drop_index(
            "ix_pre_registrations_email",
            table_name="pre_registrations",
        )

        op.drop_table("pre_registrations")

    user_columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    if "is_admin" in user_columns:
        op.drop_column("users", "is_admin")
