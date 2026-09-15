"""Pydantic schemas for note comments."""

from __future__ import annotations

from uuid import UUID

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    """Schema for posting a comment.

    @username references in the body trigger a notification to the matching
    user when an account exists.
    """

    body: str = Field(min_length=1, max_length=2000)


class CommentResponse(BaseModel):
    """Schema for a comment, with the author's username resolved."""

    id: UUID
    note_id: UUID
    author_id: UUID
    author_username: str
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
