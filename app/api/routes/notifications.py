# app/api/routes/notifications.py
"""Notification REST endpoints: list, read, archive, and bulk actions."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.user import User
from app.schemas.notification import (
    BulkNotificationAction,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

logger = logging.getLogger("app")
router = APIRouter()


@router.get("", response_model=list[NotificationResponse], summary="List notifications")
def list_notifications(
    unread_only: bool = Query(False),
    archived: bool = Query(False),
    limit: int = Query(50, le=200),
    skip: int = Query(0),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    return NotificationService.list_notifications(
        db,
        user_id=current_user.id,
        unread_only=unread_only,
        archived=archived,
        limit=limit,
        skip=skip,
    )


# app/api/routes/notifications.py — line 48, was over 88 chars
@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UnreadCountResponse:
    """Return the current user's unread notification count."""
    count = NotificationService.unread_count(db, current_user.id)
    return UnreadCountResponse(count=count)

@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(
    notification_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    try:
        return NotificationService.mark_read(db, notification_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Notification not found") from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Access denied") from exc


@router.post("/read-all")
def mark_all_read(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    return {"updated": NotificationService.mark_all_read(db, current_user.id)}


@router.post("/{notification_id}/archive", response_model=NotificationResponse)
def archive_notification(
    notification_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    try:
        return NotificationService.set_archived(
            db, notification_id, current_user.id, archived=True
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Notification not found") from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Access denied") from exc


@router.post("/{notification_id}/unarchive", response_model=NotificationResponse)
def unarchive_notification(
    notification_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    try:
        return NotificationService.set_archived(
            db, notification_id, current_user.id, archived=False
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Notification not found") from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Access denied") from exc


@router.post("/bulk", summary="Bulk mark-read, archive, unarchive, or delete")
def bulk_notification_action(
    payload: BulkNotificationAction,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    updated = NotificationService.bulk_action(
        db, ids=payload.ids, user_id=current_user.id, action=payload.action
    )
    return {"updated": updated}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        NotificationService.delete(db, notification_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Notification not found") from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Access denied") from exc
