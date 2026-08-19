"""Pydantic schemas for the public contact form."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ContactMessageCreate(BaseModel):
    """Schema for a public contact form submission. No auth required."""

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)


class ContactMessageResponse(BaseModel):
    """Schema for returning a contact message. Developer-only."""

    id: str
    name: str
    email: str
    subject: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
