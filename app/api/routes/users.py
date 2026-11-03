"""User profile management and public profile endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.errors import NotFoundError
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.user_response_service import build_user_response
from app.services.user_service import UserService

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UserProfileUpdate(BaseModel):
    """Allowlisted fields users can modify on their own profiles."""

    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=30,
    )
    full_name: str | None = Field(
        default=None,
        max_length=255,
    )
    avatar_url: str | None = Field(
        default=None,
        max_length=2_048,
    )
    bio: str | None = Field(
        default=None,
        max_length=1_000,
    )

    @field_validator("username")
    @classmethod
    def username_cannot_be_null(
        cls,
        value: str | None,
    ) -> str:
        """Require username to be omitted rather than explicitly null."""
        if value is None:
            raise ValueError("username cannot be null")

        return value


class UserPublicResponse(BaseModel):
    """Public profile excluding private account and internal information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


# ---------------------------------------------------------------------------
# Current user profile
# ---------------------------------------------------------------------------


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update my profile",
)
def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update the authenticated user's editable profile fields."""
    user = UserService.update_profile(
        db,
        user=current_user,
        data=payload.model_dump(exclude_unset=True),
    )

    return build_user_response(db, user)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete my account",
)
def delete_account(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete the authenticated user's account."""
    UserService.delete_account(
        db,
        user=current_user,
    )


# ---------------------------------------------------------------------------
# Public profiles
# ---------------------------------------------------------------------------


@router.get(
    "/{user_id}",
    response_model=UserPublicResponse,
    summary="Get a public profile",
)
def get_public_user(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> UserPublicResponse:
    """Retrieve a user's publicly visible profile."""
    try:
        user = UserService.get_by_id(
            db,
            user_id=user_id,
        )

        return UserPublicResponse.model_validate(user)

    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from exc
