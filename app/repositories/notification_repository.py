# app/repositories/notification_repository.py
"""Repository for notification persistence and querying."""

from typing import Any, cast

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Repository for CRUD and bulk operations on Notification models."""

    model = Notification

    @classmethod
    def get_user_notifications(
        cls,
        db: Session,
        user_id: str,
        unread_only: bool = False,
        archived: bool = False,
        limit: int = 50,
        skip: int = 0,
    ) -> list[Notification]:
        """Fetch a user's notifications, optionally filtered to unread/archived."""
        query = db.query(cls.model).filter(
            cls.model.recipient_id == user_id,
            cls.model.archived == archived,
        )
        if unread_only:
            query = query.filter(cls.model.read.is_(False))
        return (
            query.order_by(cls.model.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def count_unread(cls, db: Session, user_id: str) -> int:
        """Count a user's unread notifications."""
        return (
            db.query(cls.model)
            .filter(cls.model.recipient_id == user_id, cls.model.read.is_(False))
            .count()
        )

    @classmethod
    def mark_all_read(cls, db: Session, user_id: str) -> int:
        """Mark every unread notification for a user as read."""
        updated = (
            db.query(cls.model)
            .filter(cls.model.recipient_id == user_id, cls.model.read.is_(False))
            .update({"read": True})
        )
        db.commit()
        return updated

    @classmethod
    def bulk_update(
        cls, db: Session, ids: list[str], user_id: str, data: dict[str, Any]
    ) -> int:
        """Apply `data` to every notification in `ids` owned by `user_id`.

        Scoped to `recipient_id == user_id` so a caller can't smuggle in
        someone else's notification id and mutate it via this endpoint.
        """
        # SQLAlchemy's Query.update() stub wants Dict[_DMLColumnArgument, Any];
        # plain dict[str, Any] is rejected by Pylance due to dict's invariant
        # typing, even though string column names are valid at runtime. This
        # cast only affects the type checker, not the actual call.
        updated = (
            db.query(cls.model)
            .filter(cls.model.id.in_(ids), cls.model.recipient_id == user_id)
            .update(cast(dict[Any, Any], data), synchronize_session=False)
        )
        db.commit()
        return updated

    @classmethod
    def bulk_delete(cls, db: Session, ids: list[str], user_id: str) -> int:
        """Delete every notification in `ids` owned by `user_id`."""
        deleted = (
            db.query(cls.model)
            .filter(cls.model.id.in_(ids), cls.model.recipient_id == user_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted
