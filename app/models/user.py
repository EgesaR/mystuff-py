"""Database models for user management."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.auth import PasswordResetToken, RefreshToken
    from app.models.file import File
    from app.models.folder import Folder
    from app.models.media import AudioNote, MediaItem
    from app.models.note import Note
    from app.models.notification import Notification
    from app.models.system_log import SystemLog


class User(Base, UUIDMixin, TimestampMixin):
    """Database model for user accounts."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    folders: Mapped[list["Folder"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    files: Mapped[list["File"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    notes: Mapped[list["Note"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    audio_notes: Mapped[list["AudioNote"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    media_items: Mapped[list["MediaItem"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    notifications_received: Mapped[list["Notification"]] = relationship(
        foreign_keys="Notification.recipient_id",
        back_populates="recipient",
    )

    notifications_sent: Mapped[list["Notification"]] = relationship(
        foreign_keys="Notification.sender_id",
        back_populates="sender",
    )

    logs: Mapped[list["SystemLog"]] = relationship(
        back_populates="user",
    )
