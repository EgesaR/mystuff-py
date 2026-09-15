from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.onboarding import BetaSignup, UserOnboarding
from app.repositories.base_repository import BaseRepository


class OnboardingRepository(BaseRepository[UserOnboarding]):
    """Repository for onboarding records."""

    model = UserOnboarding

    @classmethod
    def get_by_user(
        cls,
        db: Session,
        user_id: UUID,
    ) -> UserOnboarding | None:
        """Get onboarding state for a user."""
        return (
            db.query(cls.model)
            .filter(cls.model.user_id == user_id)
            .first()
        )

    @classmethod
    def create_for_user(
        cls,
        db: Session,
        *,
        user_id: UUID,
        version: int,
    ) -> UserOnboarding:
        """Create initial onboarding state."""
        onboarding = cls.model(
            user_id=user_id,
            version=version,
            completed=False,
            skipped=False,
            current_step="welcome",
        )

        db.add(onboarding)
        db.flush()

        return onboarding

    @classmethod
    def get_or_create(
        cls,
        db: Session,
        *,
        user_id: UUID,
        version: int,
    ) -> UserOnboarding:
        """Get onboarding state or create it."""
        onboarding = cls.get_by_user(
            db,
            user_id,
        )

        if onboarding is not None:
            return onboarding

        return cls.create_for_user(
            db,
            user_id=user_id,
            version=version,
        )

    @classmethod
    def update_step(
        cls,
        db: Session,
        onboarding: UserOnboarding,
        *,
        step: str,
        version: int,
    ) -> UserOnboarding:
        """Update onboarding progress."""
        onboarding.version = version
        onboarding.current_step = step
        onboarding.completed = step == "complete"
        onboarding.skipped = False

        if step == "complete":
            onboarding.completed_at = datetime.now(UTC)
        else:
            onboarding.completed_at = None

        db.flush()

        return onboarding

    @classmethod
    def complete(
        cls,
        db: Session,
        onboarding: UserOnboarding,
        *,
        version: int,
    ) -> UserOnboarding:
        """Mark onboarding as completed."""
        onboarding.version = version
        onboarding.completed = True
        onboarding.skipped = False
        onboarding.current_step = "complete"
        onboarding.completed_at = datetime.now(UTC)

        db.flush()

        return onboarding

    @classmethod
    def skip(
        cls,
        db: Session,
        onboarding: UserOnboarding,
        *,
        version: int,
    ) -> UserOnboarding:
        """Mark onboarding as skipped."""
        onboarding.version = version
        onboarding.completed = False
        onboarding.skipped = True
        onboarding.completed_at = None

        db.flush()

        return onboarding

    @classmethod
    def reset_for_version(
        cls,
        db: Session,
        onboarding: UserOnboarding,
        *,
        version: int,
    ) -> UserOnboarding:
        """Reset onboarding when a new version is released."""
        onboarding.version = version
        onboarding.completed = False
        onboarding.skipped = False
        onboarding.completed_at = None
        onboarding.current_step = "welcome"

        db.flush()

        return onboarding

    @staticmethod
    def get_beta(
        db: Session,
        user_id: UUID,
    ) -> BetaSignup | None:
        """Get a user's beta signup."""
        return (
            db.query(BetaSignup)
            .filter(BetaSignup.user_id == user_id)
            .first()
        )

    @staticmethod
    def create_beta(
        db: Session,
        *,
        user_id: UUID,
        interested: bool,
    ) -> BetaSignup:
        """Create a beta signup."""
        timestamp = datetime.now(UTC)

        beta = BetaSignup(
            user_id=user_id,
            interested=interested,
            status=(
                "interested"
                if interested
                else "not_interested"
            ),
            signed_up_at=(
                timestamp
                if interested
                else None
            ),
        )

        db.add(beta)
        db.flush()

        return beta

    @staticmethod
    def update_beta(
        db: Session,
        beta: BetaSignup,
        *,
        interested: bool,
    ) -> BetaSignup:
        """Update beta interest.

        A previous signup timestamp is retained so that
        it represents the first beta signup event.
        """
        beta.interested = interested
        beta.status = (
            "interested"
            if interested
            else "not_interested"
        )

        if interested and beta.signed_up_at is None:
            beta.signed_up_at = datetime.now(UTC)

        db.flush()

        return beta
