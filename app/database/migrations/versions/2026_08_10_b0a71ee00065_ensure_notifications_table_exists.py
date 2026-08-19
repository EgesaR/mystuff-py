"""ensure notifications table exists

Revision ID: <will be filled automatically>
Revises: 9250611d787a
Create Date: ...
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "..."          # leave whatever Alembic generated
down_revision: Union[str, None] = "9250611d787a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if "notifications" in inspector.get_table_names():
        # Table already exists (local development) → do nothing
        return

    # Create the enum type if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notificationtype AS ENUM (
                'system_alert',
                'invite',
                'product_update',
                'info',
                'success',
                'warning',
                'error',
                'mention',
                'new_message',
                'comment',
                'SHARE_INVITE'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "system_alert", "invite", "product_update",
                "info", "success", "warning", "error",
                "mention", "new_message", "comment",
                "SHARE_INVITE",
                name="notificationtype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("read", sa.Boolean(),
                  server_default="false", nullable=False),
        sa.Column("recipient_id", sa.String(),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sender_id", sa.String(),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("archived", sa.Boolean(),
                  server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    # Optional – only if you are sure nothing else uses the enum:
    # op.execute("DROP TYPE IF EXISTS notificationtype")
