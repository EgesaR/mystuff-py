"""Pydantic schemas for documentation pages."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocPageCreate(BaseModel):
    """Schema for creating a docs page. Developer-only."""

    title: str = Field(min_length=3, max_length=200)
    category: str = Field(default="Getting Started", max_length=80)
    content: str = Field(min_length=1)
    order: int = 0


class DocPageUpdate(BaseModel):
    """Schema for updating a docs page. Developer-only. All fields optional."""

    title: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=80)
    content: str | None = None
    order: int | None = None


class DocPageResponse(BaseModel):
    """Schema for returning a single docs page."""

    id: str
    slug: str
    category: str
    title: str
    content: str
    order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocPageSummary(BaseModel):
    """Lightweight schema for the docs sidebar/listing page."""

    id: str
    slug: str
    category: str
    title: str
    order: int

    model_config = ConfigDict(from_attributes=True)
