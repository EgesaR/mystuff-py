"""Pydantic schemas for notes and editor note indexes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)

from app.schemas.common import JsonValue
from app.schemas.media import NoteMediaResponse


class NoteCreate(BaseModel):
    """Create a note with an optional client-generated canonical UUID."""

    id: UUID | None = None
    title: str = Field(
        default="Untitled Note",
        max_length=255,
    )
    content: dict[str, JsonValue] | None = None
    folder_id: UUID | None = None
    color: str = Field(
        default="#ffffff",
        max_length=20,
    )


class NoteUpdate(BaseModel):
    """Update legacy note content or metadata.

    Folder changes are handled through the dedicated folder endpoint.
    Explicit null values for title and color are rejected.
    """

    title: str | None = Field(
        default=None,
        max_length=255,
    )
    content: dict[str, JsonValue] | None = None
    color: str | None = Field(
        default=None,
        max_length=20,
    )
    pinned: bool | None = None

    @field_validator("title", "color")
    @classmethod
    def reject_explicit_null(
        cls,
        value: str | None,
    ) -> str | None:
        """Require clients to omit unchanged fields instead of sending null."""
        if value is None:
            raise ValueError("This field cannot be null; omit it to leave it unchanged")
        return value


class NoteResponse(BaseModel):
    """API response schema for a note."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: dict[str, JsonValue] | None
    plain_text: str | None
    color: str
    pinned: bool
    media: list[NoteMediaResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_serializer("content")
    def hide_encrypted_editor_snapshot(
        self,
        value: dict[str, JsonValue] | None,
    ) -> dict[str, JsonValue] | None:
        """Prevent encrypted editor snapshots from leaking through note APIs."""
        if isinstance(value, dict) and any(key.startswith("_editor_snapshot_") for key in value):
            return None

        return value


class EditorNoteSummary(BaseModel):
    """Lightweight editor index entry.

    Full editor documents are retrieved separately through the snapshot API.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    id: str
    title: str

    created_at: int = Field(alias="createdAt")
    updated_at: int = Field(alias="updatedAt")

    revision: int

    has_editor_document: bool = Field(alias="hasEditorDocument")
    requires_migration: bool = Field(alias="requiresMigration")

    pinned: bool
    folder_id: UUID | None = Field(alias="folderId")
    color: str
