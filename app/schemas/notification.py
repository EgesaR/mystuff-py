# app/schemas/notification.py
"""Notification schema definitions for data validation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationType


class NotificationCreate(BaseModel):
    """Schema for creating a new notification."""

    title: str = Field(
        max_length=255,
    )
    message: str
    type: NotificationType
    recipient_id: UUID
    sender_id: UUID | None = None
    link: str | None = None


class NotificationResponse(BaseModel):
    """Schema for notification response payloads."""

    id: UUID
    title: str
    message: str
    type: NotificationType
    read: bool
    recipient_id: UUID
    sender_id: UUID | None
    link: str | None
    created_at: datetime
    updated_at: datetime
    archived: bool
    model_config = ConfigDict(
        from_attributes=True,
    )


class BulkNotificationAction(BaseModel):
    ids: list[UUID]
    action: Literal["read", "archive", "unarchive", "delete"]


class UnreadCountResponse(BaseModel):
    """Schema for returning the count of unread notifications."""

    count: int
