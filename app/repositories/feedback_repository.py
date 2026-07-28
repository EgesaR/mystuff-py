"""Feedback repository handling database queries for Feedback models."""

from sqlalchemy.orm import Session, joinedload

from app.models.feedback import Feedback
from app.repositories.base_repository import BaseRepository


class FeedbackRepository(BaseRepository[Feedback]):
    """Repository class for executing database operations on Feedback records."""

    model: type[Feedback] = Feedback

    @classmethod
    def get_all_with_users(cls, db: Session) -> list[Feedback]:
        """Retrieve every feedback item, newest first, with the submitter eager-loaded.

        Args:
            db (Session): Database session.

        Returns:
            list[Feedback]: List of Feedback.
        """
        return (
            db.query(cls.model)
            .options(joinedload(cls.model.user))
            .order_by(cls.model.created_at.desc())
            .all()
        )

    @classmethod
    def get_user_feedback(cls, db: Session, user_id: str) -> list[Feedback]:
        """Retrieve feedback submitted by a specific user.

        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.

        Returns:
            list[Feedback]: List of Feedback.
        """
        return (
            db.query(cls.model)
            .filter(cls.model.user_id == user_id)
            .order_by(cls.model.created_at.desc())
            .all()
        )
