"""Documentation page database model definition module."""
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin


class DocPage(Base, UUIDMixin, TimestampMixin):
    """Database model representing a single docs article."""

    __tablename__ = "doc_pages"

    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    category: Mapped[str] = mapped_column(
        String(80), default="Getting Started")
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)  # markdown source
    order: Mapped[int] = mapped_column(Integer, default=0)
