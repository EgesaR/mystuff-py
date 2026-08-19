"""Feedback schema definitions for data validation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    """Schema for submitting new feedback."""

    message: str = Field(min_length=1, max_length=4000)
    category: Literal["bug", "feature", "general", "praise"] = "general"
    attached_logs: str | None = Field(default=None, max_length=100000)


class FeedbackStatusUpdate(BaseModel):
    """Schema for a developer updating feedback status."""

    status: Literal["new", "reviewed", "resolved"]


class FeedbackUserSummary(BaseModel):
    """Minimal user info attached to a feedback item."""

    id: str
    username: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class FeedbackResponse(BaseModel):
    """Schema for feedback response payloads."""

    id: str
    message: str
    category: str
    status: str
    attached_logs: str | None = None
    user: FeedbackUserSummary
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
