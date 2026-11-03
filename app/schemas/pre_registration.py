from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PreRegistrationCreate(BaseModel):
    email: EmailStr
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )


class PreRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    name: str | None

    verified: bool
    verified_at: datetime | None

    subscribed: bool
    unsubscribed_at: datetime | None

    launch_email_sent_at: datetime | None
    last_email_error: str | None

    created_at: datetime
    updated_at: datetime


class PreRegistrationSignupResponse(BaseModel):
    message: str


class PreRegistrationVerifyResponse(BaseModel):
    verified: bool
    message: str


class PreRegistrationUnsubscribeResponse(BaseModel):
    subscribed: bool
    message: str


class AdminPreRegistrationListResponse(BaseModel):
    items: list[PreRegistrationResponse]
    total: int
    page: int
    page_size: int

    verified_count: int
    subscribed_count: int
    sent_count: int


class LaunchEmailRequest(BaseModel):
    subject: str = Field(
        min_length=3,
        max_length=200,
    )

    message: str = Field(
        min_length=1,
        max_length=20_000,
    )


class LaunchEmailResponse(BaseModel):
    queued: int
    message: str
