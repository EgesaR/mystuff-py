from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import GUID
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserOnboarding(Base, UUIDMixin, TimestampMixin):
    """Store onboarding progress for a user."""

    __tablename__ = "user_onboarding"

    ONBOARDING_STEPS: ClassVar[tuple[str, ...]] = (
        "welcome",
        "workspace",
        "features",
        "feedback",
        "beta",
        "complete",
    )

    id: Mapped[UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid4)

    user_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    skipped: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    current_step: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="welcome",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(
        back_populates="onboarding",
    )

    @property
    def required(self) -> bool:
        """Return whether the user still needs to complete onboarding."""
        return not self.completed and not self.skipped

    @property
    def step(self) -> int:
        """Return the numeric frontend step index."""
        try:
            return self.ONBOARDING_STEPS.index(self.current_step)
        except ValueError:
            return 0


class BetaSignup(Base, UUIDMixin, TimestampMixin):
    """Store a user's beta-testing preference."""

    __tablename__ = "beta_signups"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_beta_signups_user",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid4)

    user_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    interested: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="not_interested",
    )

    signed_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(
        back_populates="beta_signup",
    )
