from __future__ import annotations

from datetime import datetime
from uuid import UUID

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


class BetaResponse(BaseModel):
    """Beta-testing state exposed by the API."""

    model_config = ConfigDict(from_attributes=True)

    interested: bool
    status: str
    signed_up_at: datetime | None = None


class FeedbackResponse(BaseModel):
    """Feedback state exposed by the API."""

    model_config = ConfigDict(from_attributes=True)

    submitted: bool
    last_submitted_at: datetime | None = None


class UserOnboardingResponse(BaseModel):
    """Public onboarding state."""

    model_config = ConfigDict(from_attributes=True)

    required: bool
    completed: bool
    step: int
    skipped: bool
    version: int
    completed_at: datetime | None = None

    beta: BetaResponse
    feedback: FeedbackResponse


class UserResponse(BaseModel):
    """Public authenticated user profile response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    username: str
    full_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    is_active: bool
    is_developer: bool
    is_admin: bool

    onboarding: UserOnboardingResponse
