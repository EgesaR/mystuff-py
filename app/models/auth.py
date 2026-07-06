"""Authentication and password reset models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    """Database model for storing refresh tokens."""

    __tablename__ = "refresh_tokens"

    token: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
    )

    user: Mapped[User] = relationship(
        back_populates="refresh_tokens",
    )


class PasswordResetToken(Base, UUIDMixin, TimestampMixin):
    """Database model for storing password reset tokens."""

    __tablename__ = "password_reset_tokens"

    token: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )

    used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
    )

    user: Mapped[User] = relationship(
        back_populates="password_reset_tokens",
    )
