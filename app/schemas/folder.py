"""Pydantic models for folder structure and management."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FolderCreate(BaseModel):
    """Schema for creating a new folder."""

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    color: str = "#6366f1"

    parent_id: str | None = None


class FolderUpdate(BaseModel):
    """Schema for updating an existing folder's properties."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    color: str | None = None


class FolderResponse(BaseModel):
    """Schema for returning folder details."""

    id: str
    name: str
    color: str
    parent_id: str | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
