"""Database model for file storage."""

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import MediaType

if TYPE_CHECKING:
    from app.models.folder import Folder
    from app.models.user import User


class File(Base, UUIDMixin, TimestampMixin):
    """Database model representing a file uploaded by a user."""

    __tablename__ = "files"

    name: Mapped[str] = mapped_column(
        String(255),
    )

    original_name: Mapped[str] = mapped_column(
        String(255),
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
    )

    url: Mapped[str] = mapped_column(
        String(500),
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    size_bytes: Mapped[int] = mapped_column(
        Integer,
    )

    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType),
    )

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    folder_id: Mapped[str | None] = mapped_column(
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
    )

    owner: Mapped["User"] = relationship(
        back_populates="files",
    )

    folder: Mapped["Folder | None"] = relationship(
        back_populates="files",
    )
