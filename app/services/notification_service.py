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
        """List a user's notifications, filtered by read/archived state."""
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
        """Count a user's unread notifications."""
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
        """Create a notification and push it to the recipient over WS.

        `notification_type` is required rather than defaulted — confirm the
        real member name against `app.models.enums.NotificationType` at each
        call site (e.g. the file-upload notification) rather than assuming
        one here.
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
        """Mark a single notification as read, if owned by `user_id`."""
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
        """Mark every unread notification for `user_id` as read."""
        return NotificationRepository.mark_all_read(db, user_id=user_id)

    @staticmethod
    def set_archived(
        db: Session, notification_id: str, user_id: str, archived: bool
    ) -> Any:
        """Archive or unarchive a single notification owned by `user_id`."""
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
        """Apply a bulk read/archive/unarchive/delete action to `ids`."""
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
        """Permanently delete a single notification owned by `user_id`."""
        notification = NotificationRepository.get(db, notification_id)
        if not notification:
            raise NotFoundError("Notification not found")
        if notification.recipient_id != user_id:
            raise PermissionDeniedError("Access denied")
        NotificationRepository.delete(db, db_obj=notification)
    
