"""Database models for collections — cross-folder groupings of files.

Unlike a Folder (a strict one-parent hierarchy a file physically lives in),
a Collection is a many-to-many "tag" layer: a file can belong to any number
of collections, in any number of folders, without being moved. This is
what makes a collection a *unique* grouping — two collections can overlap
on the same file, which two folders never can.

To wire this in:
  1. Add this file (it registers itself on `Base.metadata` automatically).
  2. Make sure wherever your models are imported for Alembic autogenerate /
     app startup, `app.models.collection` is imported too (e.g. alongside
     the other `from app.models import ...` lines).
  3. Run `alembic revision --autogenerate -m "add collections"` then
     `alembic upgrade head`.

Deliberately NOT touching app/models/user.py or app/models/file.py — the
relationships below are one-directional (Collection -> User / File) so
this ships without requiring edits to files outside this feature. If you
want `user.collections` navigation, add
`collections: Mapped[list["Collection"]] = relationship(back_populates="owner")`
to User yourself and flip `owner: Mapped["User"] = relationship()` below to
`relationship(back_populates="collections")`.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Collection(Base, UUIDMixin, TimestampMixin):
    """A named, colored grouping of files that can span folders."""

    __tablename__ = "collections"
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_collection_owner_name"),
    )

    name: Mapped[str] = mapped_column(String(255))
    color: Mapped[str] = mapped_column(String(20), default="#6366f1")

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    owner: Mapped["User"] = relationship()


class CollectionFile(Base, UUIDMixin, TimestampMixin):
    """Join row linking a File to a Collection (many-to-many membership)."""

    __tablename__ = "collection_files"
    __table_args__ = (
        UniqueConstraint("collection_id", "file_id",
                         name="uq_collection_file"),
    )

    collection_id: Mapped[str] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"),
    )
    file_id: Mapped[str] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"),
    )

    collection: Mapped["Collection"] = relationship()
