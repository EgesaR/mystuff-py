"""Database models for application system logging."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import LogLevel

if TYPE_CHECKING:
    from app.models.user import User


class SystemLog(Base, UUIDMixin, TimestampMixin):
    """Database model for capturing system logs."""

    __tablename__ = "system_logs"

    level: Mapped[LogLevel] = mapped_column(
        Enum(LogLevel),
        index=True,
    )

    label: Mapped[str] = mapped_column(
        String(100),
    )

    message: Mapped[str] = mapped_column(
        Text,
    )

    source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Structured payload for logs that carry more than a plain message —
    # e.g. accuracy logs store {mode, accuracy_type, word_accuracy, ...} here
    # so it can be queried/aggregated without parsing the message string.
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped["User | None"] = relationship(
        back_populates="logs",
    )
