import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.schemas.user import BetaResponse, FeedbackResponse, UserOnboardingResponse, UserResponse
from app.services.onboarding_service import OnboardingService

logger = logging.getLogger("app")


def onboarding_step_index(current_step: str) -> int:
    """Translate persisted onboarding step names into stable UI indexes."""
    try:
        return settings.ONBOARDING_STEPS.index(current_step)
    except ValueError:
        logger.warning("Unknown onboarding step '%s'; defaulting to 0", current_step)
        return 0


def build_user_response(db: Session, user: User) -> UserResponse:
    """Build a user response with the separate onboarding recording composed in."""
    onboarding = OnboardingService.build_state(db, user)

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        is_active=user.is_active,
        is_developer=user.is_developer,
        is_admin=user.is_admin,
        onboarding=UserOnboardingResponse(
            required=onboarding.required,
            completed=onboarding.completed,
            step=onboarding_step_index(onboarding.current_step),
            skipped=onboarding.skipped,
            version=onboarding.version,
            completed_at=onboarding.completed_at,
            beta=BetaResponse(interested=onboarding.beta.interested, status=onboarding.beta.status, signed_up_at=onboarding.beta.signed_up_at),
            feedback=FeedbackResponse(submitted=onboarding.feedback.submitted, last_submitted_at=onboarding.feedback.last_submitted_at),
        ),
    )
