"""Note schema definitions for data validation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import JsonValue
from app.schemas.media import NoteMediaResponse


class NoteCreate(BaseModel):
    """Schema for creating a new note."""

    title: str = Field(
        default="Untitled Note",
        max_length=255,
    )
    content: dict[str, JsonValue] | None = None
    folder_id: str | None = None
    color: str = "#ffffff"


class NoteUpdate(BaseModel):
    """Schema for updating an existing note."""

    title: str | None = Field(
        default=None,
        max_length=255,
    )
    content: dict[str, JsonValue] | None = None
    color: str | None = None
    pinned: bool | None = None


class NoteResponse(BaseModel):
    """Schema for note response payloads."""

    id: str
    title: str
    content: dict[str, JsonValue] | None
    plain_text: str | None
    color: str
    pinned: bool
    media: list[NoteMediaResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
