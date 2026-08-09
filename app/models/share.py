"""Generic share grant owner -> target_user for any resource type."""

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import SharePermission, ShareResourceType, ShareStatus

if TYPE_CHECKING:
    from app.models.user import User


class Share(Base, UUIDMixin,  TimestampMixin):
    __tablename__ = "shares"

    resource_type: Mapped[ShareResourceType] = mapped_column(
        Enum(ShareResourceType))
    resource_id: Mapped[str] = mapped_column(String(36))

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"))
    target_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    permission: Mapped[SharePermission] = mapped_column(
        Enum(SharePermission), default=SharePermission.VIEW)
    status: Mapped[ShareStatus] = mapped_column(
        Enum(ShareStatus), default=ShareStatus.PENDING)

    # The opaque, encrypted "shared id" - this is what goes in links/notifications
    # instead of exposing resource_id/owner_id directly.
    token: Mapped[str] = mapped_column(Text, unique=True, index=True)

    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])
    target_user: Mapped["User | None"] = relationship(
        foreign_keys=[target_user_id])
