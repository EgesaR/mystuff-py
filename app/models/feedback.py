"""Feedback database model definition module."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import GUID
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Feedback(Base, UUIDMixin, TimestampMixin):
    """Database model representing user-submitted feedback."""

    __tablename__ = "feedback"

    id: Mapped[UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid4,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attached_logs: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(30),
        default="general",
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="new",
        nullable=False,
    )

    rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    user: Mapped["User"] = relationship()
