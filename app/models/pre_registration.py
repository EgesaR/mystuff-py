from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


class PreRegistration(Base):
    """User who has registered interest in the upcoming My Stuff launch."""

    __tablename__ = "pre_registrations"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
        index=True,
    )

    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Double opt-in verification
    # ------------------------------------------------------------------

    verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verification_token_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    verification_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    subscribed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    unsubscribed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    unsubscribe_token: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
        default=lambda: secrets.token_urlsafe(48),
    )

    # ------------------------------------------------------------------
    # Campaign tracking
    # ------------------------------------------------------------------

    launch_email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_email_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Account conversion tracking
    # ------------------------------------------------------------------

    converted_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=utc_now,
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    __table_args__ = (
        Index(
            "ix_pre_registrations_verified_subscribed",
            "verified",
            "subscribed",
        ),
        Index(
            "ix_pre_registrations_created_at",
            "created_at",
        ),
    )
