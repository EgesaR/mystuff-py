"""Blog post database model definition module."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class BlogPost(Base, UUIDMixin, TimestampMixin):
    """Database model representing a published blog article."""

    __tablename__ = "blog_posts"

    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    excerpt: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)  # markdown source

    cover_image_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True)
    tags: Mapped[str | None] = mapped_column(
        String(300), nullable=True)  # comma-separated

    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    author_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"))
    author: Mapped["User"] = relationship()
