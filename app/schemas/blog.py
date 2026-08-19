"""Pydantic schemas for blog post management."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BlogAuthorSummary(BaseModel):
    """Minimal author info attached to a blog post."""

    id: str
    username: str

    model_config = ConfigDict(from_attributes=True)


class BlogPostCreate(BaseModel):
    """Schema for creating a blog post. Developer-only."""

    title: str = Field(min_length=3, max_length=200)
    excerpt: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)
    cover_image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_published: bool = False

    @field_validator("tags")
    @classmethod
    def limit_tags(cls, v: list[str]) -> list[str]:
        """Cap tags at 8 so listings and OG keywords don't run away."""
        return v[:8]


class BlogPostUpdate(BaseModel):
    """Schema for updating a blog post. Developer-only. All fields optional."""

    title: str | None = Field(default=None, max_length=200)
    excerpt: str | None = Field(default=None, max_length=300)
    content: str | None = None
    cover_image_url: str | None = None
    tags: list[str] | None = None
    is_published: bool | None = None


class BlogPostResponse(BaseModel):
    """Schema for returning a single blog post."""

    id: str
    slug: str
    title: str
    excerpt: str
    content: str
    cover_image_url: str | None
    tags: list[str]
    is_published: bool
    published_at: datetime | None
    author: BlogAuthorSummary
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("tags", mode="before")
    @classmethod
    def split_tags(cls, v: object) -> list[str]:
        """Model stores tags as a comma-separated string; expand to a list here."""
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]

        if isinstance(v, str):
            return [str(t).strip() for t in v if str(t).strip()]

        return []


class BlogPostSummary(BaseModel):
    """Lightweight schema for blog listing pages."""

    id: str
    slug: str
    title: str
    excerpt: str
    cover_image_url: str | None
    tags: list[str]
    is_published: bool
    published_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("tags", mode="before")
    @classmethod
    def split_tags(cls, v: object) -> list[str]:
        """Model stores tags as a comma-separated string; expand to a list here."""
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]

        if isinstance(v, str):
            return [str(t).strip() for t in v if str(t).strip()]

        return []
