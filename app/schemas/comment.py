"""Pydantic schemas for note comments."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    """Schema for posting a comment. @username in the body triggers a notificationto to that user if their account exists."""

    body: str = Field(min_length=1, max_length=2000)


class CommentResponse(BaseModel):
    """Schema for a comment, with the author's username resolved."""

    id: str
    note_id: str
    author_id: str
    author_username: str
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
