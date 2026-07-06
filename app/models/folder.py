"""Database model for folder organization."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.file import File
    from app.models.user import User


class Folder(Base, UUIDMixin, TimestampMixin):
    """Database model representing a user folder."""

    __tablename__ = "folders"

    name: Mapped[str] = mapped_column(
        String(255),
    )

    color: Mapped[str] = mapped_column(
        String(20),
        default="#6366f1",
    )

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"),
        nullable=True,
    )

    owner: Mapped["User"] = relationship(
        back_populates="folders",
    )

    files: Mapped[list["File"]] = relationship(
        back_populates="folder",
    )

    parent: Mapped["Folder | None"] = relationship(
        remote_side="Folder.id",
    )
