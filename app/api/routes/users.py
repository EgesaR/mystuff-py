"""User profile management endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.errors import NotFoundError
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import UserService

logger = logging.getLogger("app")
router = APIRouter()

# ... [get_profile stays the same] ...


@router.patch("/me", response_model=UserResponse, summary="Update current user profile")
def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> User:
    """Update current user profile."""
    return UserService.update_profile(
        db,
        user=current_user,
        data=payload.model_dump(exclude_unset=True),
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete account")
def delete_account(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete current user account."""
    UserService.delete_account(db, user=current_user)


@router.get("/{user_id}", response_model=UserResponse, summary="Get public profile")
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
) -> User:
    """Get a user's public profile by ID."""
    try:
        return UserService.get_by_id(db, user_id=user_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from exc
