"""Database models for media attachments and records."""

from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import NoteMediaType

if TYPE_CHECKING:
    from app.models.note import Note
    from app.models.user import User


class NoteMedia(Base, UUIDMixin, TimestampMixin):
    """Database model for media associated with a specific note."""

    __tablename__ = "note_media"

    note_id: Mapped[str] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
    )

    url: Mapped[str] = mapped_column(
        String(500),
    )

    media_type: Mapped[NoteMediaType] = mapped_column(
        Enum(NoteMediaType),
    )

    caption: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    note: Mapped["Note"] = relationship(
        back_populates="media",
    )


class AudioNote(Base, UUIDMixin, TimestampMixin):
    """Database model for audio-based notes."""

    __tablename__ = "audio_notes"

    title: Mapped[str] = mapped_column(
        String(255),
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
    )

    url: Mapped[str] = mapped_column(
        String(500),
    )

    transcript: Mapped[str | None]

    duration_sec: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    owner: Mapped["User"] = relationship(
        back_populates="audio_notes",
    )


class MediaItem(Base, UUIDMixin, TimestampMixin):
    """Database model for general media items."""

    __tablename__ = "media_items"

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
    )

    url: Mapped[str] = mapped_column(
        String(500),
    )

    thumbnail_url: Mapped[str | None]

    mime_type: Mapped[str | None]

    media_type: Mapped[NoteMediaType] = mapped_column(
        Enum(NoteMediaType),
    )

    size_bytes: Mapped[int | None]

    width: Mapped[int | None]

    height: Mapped[int | None]

    duration_sec: Mapped[float | None]

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    owner: Mapped["User"] = relationship(
        back_populates="media_items",
    )
