# app/services/notification_service.py
"""Business logic for creating, listing, and mutating notifications."""

from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.api.websocket.notifications import notification_manager
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.enums import NotificationType
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    """Service layer for notification CRUD, archiving, and bulk actions."""

    @staticmethod
    def list_notifications(
        db: Session,
        user_id: str,
        unread_only: bool = False,
        archived: bool = False,
        limit: int = 50,
        skip: int = 0,
    ) -> list[Any]:
        """List notifications for a user.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            unread_only (bool): Unread only flag.
            archived (bool): Archived flag.
            limit (int): Limit integer.
            skip (int): Skip integer.
        
        Returns:
            list[Any]: List of Any.
        """
        return NotificationRepository.get_user_notifications(
            db,
            user_id=user_id,
            unread_only=unread_only,
            archived=archived,
            limit=limit,
            skip=skip,
        )

    @staticmethod
    def unread_count(db: Session, user_id: str) -> int:
        """Count unread notifications for a user.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            int: int result.
        """
        return NotificationRepository.count_unread(db, user_id=user_id)

    @staticmethod
    def create(
        db: Session,
        recipient_id: str,
        title: str,
        message: str,
        notification_type: NotificationType,
        background_tasks: BackgroundTasks,
        link: str | None = None,
        sender_id: str | None = None,
    ) -> Any:
        """Create.
        
        Args:
            db (Session): Database session.
            recipient_id (str): Unique identifier of the target resource.
            title (str): Title string.
            message (str): Message string.
            notification_type (NotificationType): The notification type.
            background_tasks (BackgroundTasks): The background tasks.
            link (str | None): The link.
            sender_id (str | None): Unique identifier of the target resource.
        
        Returns:
            Any: Result value.
        """
        notification = NotificationRepository.create(
            db,
            {
                "recipient_id": recipient_id,
                "sender_id": sender_id,
                "title": title,
                "message": message,
                "type": notification_type,
                "link": link,
                "read": False,
            },
        )

        payload = {
            "id": str(notification.id),
            "title": notification.title,
            "message": notification.message,
            "type": notification.type.value,
            "link": notification.link,
            "read": notification.read,
            "created_at": (
                notification.created_at.isoformat() if notification.created_at else None
            ),
        }
        background_tasks.add_task(
            notification_manager.push, recipient_id, payload)

        return notification

    @staticmethod
    def mark_read(db: Session, notification_id: str, user_id: str) -> Any:
        """Mark a notification as read.
        
        Args:
            db (Session): Database session.
            notification_id (str): Unique identifier of the notification.
            user_id (str): Unique identifier of the user.
        
        Returns:
            Any: Result value.
        """
        notification = NotificationRepository.get(db, notification_id)
        if not notification:
            raise NotFoundError("Notification not found")
        if notification.recipient_id != user_id:
            raise PermissionDeniedError("Access denied")
        return NotificationRepository.update(
            db, db_obj=notification, update_data={"read": True}
        )

    @staticmethod
    def mark_all_read(db: Session, user_id: str) -> int:
        """Mark all notifications as read.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            int: int result.
        """
        return NotificationRepository.mark_all_read(db, user_id=user_id)

    @staticmethod
    def set_archived(
        db: Session, notification_id: str, user_id: str, archived: bool
    ) -> Any:
        """Set archived.
        
        Args:
            db (Session): Database session.
            notification_id (str): Unique identifier of the notification.
            user_id (str): Unique identifier of the user.
            archived (bool): Archived flag.
        
        Returns:
            Any: Result value.
        """
        notification = NotificationRepository.get(db, notification_id)
        if not notification:
            raise NotFoundError("Notification not found")
        if notification.recipient_id != user_id:
            raise PermissionDeniedError("Access denied")
        return NotificationRepository.update(
            db, db_obj=notification, update_data={"archived": archived}
        )

    @staticmethod
    def bulk_action(db: Session, ids: list[str], user_id: str, action: str) -> int:
        """Bulk action.
        
        Args:
            db (Session): Database session.
            ids (list[str]): The ids.
            user_id (str): Unique identifier of the user.
            action (str): Action string.
        
        Returns:
            int: int result.
        """
        if action == "delete":
            return NotificationRepository.bulk_delete(db, ids=ids, user_id=user_id)
        data_map = {
            "read": {"read": True},
            "archive": {"archived": True},
            "unarchive": {"archived": False},
        }
        return NotificationRepository.bulk_update(
            db, ids=ids, user_id=user_id, data=data_map[action]
        )

    @staticmethod
    def delete(db: Session, notification_id: str, user_id: str) -> None:
        """Delete.
        
        Args:
            db (Session): Database session.
            notification_id (str): Unique identifier of the notification.
            user_id (str): Unique identifier of the user.
        
        Returns:
            None: None result.
        """
        notification = NotificationRepository.get(db, notification_id)
        if not notification:
            raise NotFoundError("Notification not found")
        if notification.recipient_id != user_id:
            raise PermissionDeniedError("Access denied")
        NotificationRepository.delete(db, db_obj=notification)
    
