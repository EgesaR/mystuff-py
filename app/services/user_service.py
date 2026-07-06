"""Service module for handling business logic related to user entities."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    """Service class for managing user profile business logic."""

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> User:
        """Retrieve a user by their unique identifier."""
        user = UserRepository.get(db, user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    @staticmethod
    def delete_account(db: Session, user: User) -> None:
        """Permanently remove a user account."""
        # Ensure we pass the ID to the repository
        UserRepository.delete(db, user)

    @staticmethod
    def update_profile(db: Session, user: User, data: dict[str, Any]) -> User:
        """Update user profile fields based on a dictionary of changes."""
        return UserRepository.update(db, user, data)

    @staticmethod
    def update_avatar(db: Session, user: User, avatar_url: str) -> User:
        """Update the user's avatar URL."""
        return UserRepository.update(db, user, {"avatar_url": avatar_url.strip()})

    @staticmethod
    def deactivate_account(db: Session, user: User) -> User:
        """Deactivate a user account."""
        if not user.is_active:
            return user
        return UserRepository.update(db, user, {"is_active": False})

    @staticmethod
    def reactivate_account(db: Session, user: User) -> User:
        """Reactivate a user account."""
        if user.is_active:
            return user
        return UserRepository.update(db, user, {"is_active": True})

    @staticmethod
    def update_last_login(db: Session, user: User) -> User:
        """Update the user's last login timestamp."""
        return UserRepository.update(db, user, {"last_login": datetime.now(UTC)})
