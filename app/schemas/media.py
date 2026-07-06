"""Pydantic models for media and audio note items."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NoteMediaType


class NoteMediaResponse(BaseModel):
    """Schema for generic media items attached to a note."""

    id: str

    url: str

    media_type: NoteMediaType

    caption: str | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class AudioNoteResponse(BaseModel):
    """Schema for audio note details."""

    id: str

    title: str

    file_path: str
    url: str

    transcript: str | None

    duration_sec: float | None

    size_bytes: int | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class MediaItemResponse(BaseModel):
    """Schema for structured media items such as images or videos."""

    id: str

    title: str | None

    file_path: str
    url: str

    thumbnail_url: str | None

    mime_type: str | None

    media_type: NoteMediaType

    size_bytes: int | None

    width: int | None
    height: int | None

    duration_sec: float | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
