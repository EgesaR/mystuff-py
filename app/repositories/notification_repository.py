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
        """Retrieve user notifications.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            unread_only (bool): Unread only flag.
            archived (bool): Archived flag.
            limit (int): Limit integer.
            skip (int): Skip integer.
        
        Returns:
            list[Notification]: List of Notification.
        """
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
        """Count unread.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            int: int result.
        """
        return (
            db.query(cls.model)
            .filter(cls.model.recipient_id == user_id, cls.model.read.is_(False))
            .count()
        )

    @classmethod
    def mark_all_read(cls, db: Session, user_id: str) -> int:
        """Mark all notifications as read.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            int: int result.
        """
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
        """Bulk update.
        
        Args:
            db (Session): Database session.
            ids (list[str]): The ids.
            user_id (str): Unique identifier of the user.
            data (dict[str, Any]): The data.
        
        Returns:
            int: int result.
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
        """Bulk delete.
        
        Args:
            db (Session): Database session.
            ids (list[str]): The ids.
            user_id (str): Unique identifier of the user.
        
        Returns:
            int: int result.
        """
        deleted = (
            db.query(cls.model)
            .filter(cls.model.id.in_(ids), cls.model.recipient_id == user_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted
