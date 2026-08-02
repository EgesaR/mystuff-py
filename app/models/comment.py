"""Database model for comments attached to a note."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class NoteComment(Base, UUIDMixin, TimestampMixin):
    """A single comment thread entry on a note."""

    __tablename__ = "note_comments"

    note_id: Mapped[str] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE")
    )
    author_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    body: Mapped[str] = mapped_column(Text)

    author: Mapped["User"] = relationship()
