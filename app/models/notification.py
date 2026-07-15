# app/models/notification.py
"""Database models for system and user notifications."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import NotificationType

if TYPE_CHECKING:
    from app.models.user import User


class Notification(Base, UUIDMixin, TimestampMixin):
    """Database model for user notifications."""

    __tablename__ = "notifications"

    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    read: Mapped[bool] = mapped_column(Boolean, default=False)

    recipient_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    sender_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    link: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    recipient: Mapped["User"] = relationship(
        foreign_keys=[recipient_id],
        back_populates="notifications_received",
    )

    sender: Mapped["User | None"] = relationship(
        foreign_keys=[sender_id],
        back_populates="notifications_sent",
    )   
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
