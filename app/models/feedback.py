"""Feedback database model definition module."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Feedback(Base, UUIDMixin, TimestampMixin):
    """Database model representing user-submitted feedback."""

    __tablename__ = "feedback"

    message: Mapped[str] = mapped_column(Text)

    attached_logs: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[str] = mapped_column(String(30), default="general")

    status: Mapped[str] = mapped_column(String(20), default="new")

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    user: Mapped["User"] = relationship()
