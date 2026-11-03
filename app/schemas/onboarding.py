from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ONBOARDING_STEPS = (
    "welcome",
    "workspace",
    "features",
    "feedback",
    "beta",
    "complete",
)

BETA_INTERESTED_STATUS = "interested"
BETA_NOT_INTERESTED_STATUS = "not_interested"


class BetaState(BaseModel):
    """Current beta signup state."""

    interested: bool
    status: str
    signed_up_at: datetime | None = None


class FeedbackState(BaseModel):
    """Current feedback submission state."""

    submitted: bool
    last_submitted_at: datetime | None = None


class OnboardingState(BaseModel):
    """Complete onboarding state."""

    required: bool
    completed: bool
    skipped: bool
    version: int
    completed_at: datetime | None = None
    current_step: str
    beta: BetaState
    feedback: FeedbackState


class OnboardingUserResponse(BaseModel):
    """Authenticated user with onboarding state."""

    id: UUID
    name: str
    email: str
    onboarding: OnboardingState

    model_config = ConfigDict(
        from_attributes=True,
    )


class StepUpdate(BaseModel):
    """Move the current onboarding step."""

    version: int = Field(ge=1)
    step: str = Field(min_length=1, max_length=32)


class VersionPayload(BaseModel):
    """Payload containing an onboarding version."""

    version: int = Field(ge=1)


class BetaPayload(BaseModel):
    """Update beta-testing interest."""

    interested: bool


class FeedbackStateResponse(BaseModel):
    """Response after feedback submission."""

    submitted: bool
    submitted_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
