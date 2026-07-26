"""Database model for user workspace layouts and tab states."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class WorkspaceState(Base, UUIDMixin, TimestampMixin):
    """Stores the serialized tab and island state for a user's workspace."""

    __tablename__ = "workspace_states"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
    )

    # Use JSONB if you are using PostgreSQL, otherwise JSON
    state_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped["User"] = relationship(back_populates="workspace_state")
