"""Pydantic schemas for user profile management."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base schema containing common user fields."""

    email: EmailStr

    username: str = Field(
        min_length=3,
        max_length=50,
    )

    full_name: str | None = Field(
        default=None,
        max_length=255,
    )

    avatar_url: str | None = None
    bio: str | None = None


class UserUpdate(BaseModel):
    """Schema for updating a user's profile information."""

    full_name: str | None = Field(
        default=None,
        max_length=255,
    )

    avatar_url: str | None = None
    bio: str | None = None


class UserResponse(UserBase):
    """Schema for returning user data in API responses."""

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
