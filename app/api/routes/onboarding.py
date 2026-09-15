from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.models.user import User
from app.schemas.onboarding import (
    BetaPayload,
    OnboardingState,
    OnboardingUserResponse,
    StepUpdate,
    VersionPayload,
)
from app.services.onboarding_service import OnboardingService

router = APIRouter()


@router.get(
    "/me/onboarding",
    response_model=OnboardingUserResponse,
    summary="Get current user's onboarding state",
)
def get_onboarding(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> OnboardingUserResponse:
    """Return the authenticated user's profile and onboarding state."""
    return OnboardingService.get_user_response(
        db,
        current_user,
    )


@router.patch(
    "/me/onboarding/step",
    response_model=OnboardingState,
    summary="Save current onboarding step",
)
def save_step(
    payload: StepUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> OnboardingState:
    """Save the current onboarding step."""
    try:
        return OnboardingService.update_step(
            db,
            current_user,
            payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/me/onboarding/complete",
    response_model=OnboardingState,
    summary="Complete onboarding",
)
def complete_onboarding(
    payload: VersionPayload,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> OnboardingState:
    """Complete the current onboarding version."""
    try:
        return OnboardingService.complete(
            db,
            current_user,
            payload.version,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/me/onboarding/skip",
    response_model=OnboardingState,
    summary="Skip onboarding",
)
def skip_onboarding(
    payload: VersionPayload,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> OnboardingState:
    """Skip the current onboarding version."""
    try:
        return OnboardingService.skip(
            db,
            current_user,
            payload.version,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.patch(
    "/me/onboarding/beta",
    response_model=OnboardingState,
    summary="Update beta-testing interest",
)
def update_beta(
    payload: BetaPayload,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> OnboardingState:
    """Update beta-testing interest."""
    return OnboardingService.update_beta(
        db,
        current_user,
        payload,
    )
