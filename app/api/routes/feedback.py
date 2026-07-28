"""Feedback submission and developer review endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user, require_developer
from app.api.deps.database import get_db
from app.api.websocket.feedback import feedback_manager
from app.core.errors import NotFoundError
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackStatusUpdate,
)
from app.services.feedback_service import FeedbackService

logger = logging.getLogger("app")
router = APIRouter()


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Feedback:
    """Submit feedback as the current user.

    Args:
        payload (FeedbackCreate): Request payload.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.

    Returns:
        Feedback: Feedback result.
    """
    print("Message: ", payload.message)
    feedback = FeedbackService.submit_feedback(
        db,
        user_id=current_user.id,
        message=payload.message,
        category=payload.category,
    )

    await feedback_manager.broadcast(
        FeedbackResponse.model_validate(feedback).model_dump(mode="json")
    )

    return feedback


@router.get(
    "/mine",
    response_model=list[FeedbackResponse],
    summary="List feedback submitted by the current user",
)
def list_my_feedback(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[Feedback]:
    """List the current user's own feedback submissions.

    Args:
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.

    Returns:
        list[Feedback]: List of Feedback.
    """
    return FeedbackService.list_my_feedback(db, user_id=current_user.id)


@router.get(
    "",
    response_model=list[FeedbackResponse],
    summary="List all feedback (developer only)",
)
def list_all_feedback(
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> list[Feedback]:
    """List every feedback submission across all users. Requires developer access.

    Args:
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.

    Returns:
        list[Feedback]: List of Feedback.
    """
    return FeedbackService.list_all_feedback(db)


@router.patch(
    "/{feedback_id}/status",
    response_model=FeedbackResponse,
    summary="Update feedback status (developer only)",
)
def update_feedback_status(
    feedback_id: str,
    payload: FeedbackStatusUpdate,
    current_user: User = Depends(require_developer),
    db: Session = Depends(get_db),
) -> Feedback:
    """Update the triage status of a feedback item. Requires developer access.

    Args:
        feedback_id (str): Unique identifier of the feedback item.
        payload (FeedbackStatusUpdate): Request payload.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.

    Returns:
        Feedback: Feedback result.
    """
    try:
        return FeedbackService.update_status(
            db, feedback_id=feedback_id, status=payload.status
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found"
        ) from exc
