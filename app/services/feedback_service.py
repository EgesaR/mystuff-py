"""Feedback service module managing business logic operations for feedback."""

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.feedback import Feedback
from app.repositories.feedback_repository import FeedbackRepository


class FeedbackService:
    """Service class encapsulating application logic for Feedback management."""

    @staticmethod
    def submit_feedback(
        db: Session, user_id: str, message: str, category: str
    ) -> Feedback:
        """Submit new feedback on behalf of a user.

        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
            message (str): Feedback message body.
            category (str): Feedback category.

        Returns:
            Feedback: Feedback result.
        """
        feedback_data = {
            "user_id": user_id,
            "message": message,
            "category": category,
        }
        return FeedbackRepository.create(db, obj_in=feedback_data)

    @staticmethod
    def list_all_feedback(db: Session) -> list[Feedback]:
        """List all feedback across every user. Developer-only.

        Args:
            db (Session): Database session.

        Returns:
            list[Feedback]: List of Feedback.
        """
        return FeedbackRepository.get_all(db)

    @staticmethod
    def list_my_feedback(db: Session, user_id: str) -> list[Feedback]:
        """List feedback submitted by the current user.

        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.

        Returns:
            list[Feedback]: List of Feedback.
        """
        return FeedbackRepository.get_user_feedback(db, user_id)

    @staticmethod
    def update_status(db: Session, feedback_id: str, status: str) -> Feedback:
        """Update the triage status of a feedback item. Developer-only.

        Args:
            db (Session): Database session.
            feedback_id (str): Unique identifier of the feedback item.
            status (str): New status value.

        Returns:
            Feedback: Feedback result.
        """
        feedback = FeedbackRepository.get(db, feedback_id)
        if not feedback:
            raise NotFoundError("Feedback not found")
        return FeedbackRepository.update(
            db, db_obj=feedback, update_data={"status": status}
        )
