from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.onboarding_repository import OnboardingRepository
from app.schemas.onboarding import (
    BETA_NOT_INTERESTED_STATUS,
    BetaPayload,
    BetaState,
    FeedbackState,
    OnboardingState,
    OnboardingUserResponse,
    StepUpdate,
)


class OnboardingService:
    """Application service for onboarding workflows."""

    @staticmethod
    def get_or_create(
        db: Session,
        user_id: UUID,
    ):
        """Get onboarding state or create it."""
        return OnboardingRepository.get_or_create(
            db,
            user_id=user_id,
            version=settings.ONBOARDING_VERSION,
        )

    @staticmethod
    def ensure_current_version(
        db: Session,
        user_id: UUID,
    ):
        """Ensure onboarding uses the current application version."""
        onboarding = OnboardingService.get_or_create(
            db,
            user_id,
        )

        if onboarding.version < settings.ONBOARDING_VERSION:
            onboarding = OnboardingRepository.reset_for_version(
                db,
                onboarding,
                version=settings.ONBOARDING_VERSION,
            )

        return onboarding

    @staticmethod
    def build_state(
        db: Session,
        user: User,
    ) -> OnboardingState:
        """Build the complete onboarding state."""
        onboarding = OnboardingService.ensure_current_version(
            db,
            user.id,
        )

        beta = OnboardingRepository.get_beta(
            db,
            user.id,
        )

        feedback = FeedbackRepository.get_user_feedback(
            db,
            user.id,
        )

        latest_feedback = (
            feedback[0]
            if feedback
            else None
        )

        return OnboardingState(
            required=not (
                onboarding.completed
                or onboarding.skipped
            ),
            completed=onboarding.completed,
            skipped=onboarding.skipped,
            version=onboarding.version,
            completed_at=onboarding.completed_at,
            current_step=onboarding.current_step,
            beta=BetaState(
                interested=(
                    beta.interested
                    if beta
                    else False
                ),
                status=(
                    beta.status
                    if beta
                    else BETA_NOT_INTERESTED_STATUS
                ),
                signed_up_at=(
                    beta.signed_up_at
                    if beta
                    else None
                ),
            ),
            feedback=FeedbackState(
                submitted=latest_feedback is not None,
                last_submitted_at=(
                    latest_feedback.created_at
                    if latest_feedback
                    else None
                ),
            ),
        )

    @staticmethod
    def get_user_response(
        db: Session,
        user: User,
    ) -> OnboardingUserResponse:
        """Return the authenticated user with onboarding state."""
        return OnboardingUserResponse(
            id=user.id,
            name=user.full_name or user.username,
            email=user.email,
            onboarding=OnboardingService.build_state(
                db,
                user,
            ),
        )

    @staticmethod
    def update_step(
        db: Session,
        user: User,
        payload: StepUpdate,
    ) -> OnboardingState:
        """Update onboarding step."""
    
        print(
            "[ONBOARDING] update_step request:",
            {
                "user_id": str(user.id),
                "version": payload.version,
                "step": payload.step,
            },
        )
    
        if payload.step not in settings.ONBOARDING_STEPS:
            raise ValueError("Invalid onboarding step.")
    
        onboarding = OnboardingService.ensure_current_version(
            db,
            user.id,
        )
    
        print(
            "[ONBOARDING] BEFORE:",
            {
                "current_step": onboarding.current_step,
                "version": onboarding.version,
                "completed": onboarding.completed,
                "skipped": onboarding.skipped,
            },
        )
    
        if payload.version != onboarding.version:
            raise ValueError(
                "Onboarding version is outdated. "
                "Refresh and try again."
            )
    
        OnboardingRepository.update_step(
            db,
            onboarding,
            step=payload.step,
            version=onboarding.version,
        )
    
        print(
            "[ONBOARDING] AFTER FLUSH:",
            {
                "current_step": onboarding.current_step,
                "version": onboarding.version,
                "completed": onboarding.completed,
                "skipped": onboarding.skipped,
            },
        )
    
        db.commit()
    
        print(
            "[ONBOARDING] AFTER COMMIT:",
            {
                "current_step": onboarding.current_step,
                "version": onboarding.version,
                "completed": onboarding.completed,
                "skipped": onboarding.skipped,
            },
        )
    
        state = OnboardingService.build_state(
            db,
            user,
        )
    
        print(
            "[ONBOARDING] RESPONSE STATE:",
            {
                "current_step": state.current_step,
                "version": state.version,
                "completed": state.completed,
                "skipped": state.skipped,
            },
        )
    
        return state

    @staticmethod
    def complete(
        db: Session,
        user: User,
        version: int,
    ) -> OnboardingState:
        """Complete onboarding."""
        onboarding = OnboardingService.ensure_current_version(
            db,
            user.id,
        )

        if version != onboarding.version:
            raise ValueError(
                "Onboarding version is outdated. "
                "Refresh and try again."
            )

        OnboardingRepository.complete(
            db,
            onboarding,
            version=version,
        )

        db.commit()

        return OnboardingService.build_state(
            db,
            user,
        )

    @staticmethod
    def skip(
        db: Session,
        user: User,
        version: int,
    ) -> OnboardingState:
        """Skip onboarding."""
        onboarding = OnboardingService.ensure_current_version(
            db,
            user.id,
        )

        if version != onboarding.version:
            raise ValueError(
                "Onboarding version is outdated. "
                "Refresh and try again."
            )

        OnboardingRepository.skip(
            db,
            onboarding,
            version=version,
        )

        db.commit()

        return OnboardingService.build_state(
            db,
            user,
        )

    @staticmethod
    def update_beta(
        db: Session,
        user: User,
        payload: BetaPayload,
    ) -> OnboardingState:
        """Update beta-testing interest."""
        beta = OnboardingRepository.get_beta(
            db,
            user.id,
        )

        if beta is None:
            OnboardingRepository.create_beta(
                db,
                user_id=user.id,
                interested=payload.interested,
            )
        else:
            OnboardingRepository.update_beta(
                db,
                beta,
                interested=payload.interested,
            )

        db.commit()

        return OnboardingService.build_state(
            db,
            user,
        )
