"""Note database model definition module."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.schemas.common import JsonValue

if TYPE_CHECKING:
    from app.models.media import NoteMedia
    from app.models.user import User


class Note(Base, UUIDMixin, TimestampMixin):
    """Database model representing a user's Note instance."""

    __tablename__ = "notes"

    title: Mapped[str] = mapped_column(
        String(255),
        default="Untitled Note",
    )

    content: Mapped[dict[str, JsonValue] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    plain_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    color: Mapped[str] = mapped_column(
        String(20),
        default="#ffffff",
    )

    pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    # Added folder_id column to resolve repository type-checking errors
    folder_id: Mapped[str | None] = mapped_column(
        String(36),  # Adjust length matching your folder UUID/String strategy
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
    )

    owner: Mapped["User"] = relationship(
        back_populates="notes",
    )

    media: Mapped[list["NoteMedia"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
    )
