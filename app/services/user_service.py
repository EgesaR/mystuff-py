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
        """Retrieve by ID.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            User: User data.
        """
        user = UserRepository.get(db, user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    @staticmethod
    def delete_account(db: Session, user: User) -> None:
        """Delete account.
        
        Args:
            db (Session): Database session.
            user (User): User model instance or payload.
        
        Returns:
            None: None result.
        """
        # Ensure we pass the ID to the repository
        UserRepository.delete(db, user)

    @staticmethod
    def update_profile(db: Session, user: User, data: dict[str, Any]) -> User:
        """Update profile.
        
        Args:
            db (Session): Database session.
            user (User): User model instance or payload.
            data (dict[str, Any]): The data.
        
        Returns:
            User: User data.
        """
        return UserRepository.update(db, user, data)

    @staticmethod
    def update_avatar(db: Session, user: User, avatar_url: str) -> User:
        """Update avatar.
        
        Args:
            db (Session): Database session.
            user (User): User model instance or payload.
            avatar_url (str): Avatar url string.
        
        Returns:
            User: User data.
        """
        return UserRepository.update(db, user, {"avatar_url": avatar_url.strip()})

    @staticmethod
    def deactivate_account(db: Session, user: User) -> User:
        """Deactivate account.
        
        Args:
            db (Session): Database session.
            user (User): User model instance or payload.
        
        Returns:
            User: User data.
        """
        if not user.is_active:
            return user
        return UserRepository.update(db, user, {"is_active": False})

    @staticmethod
    def reactivate_account(db: Session, user: User) -> User:
        """Reactivate account.
        
        Args:
            db (Session): Database session.
            user (User): User model instance or payload.
        
        Returns:
            User: User data.
        """
        if user.is_active:
            return user
        return UserRepository.update(db, user, {"is_active": True})

    @staticmethod
    def update_last_login(db: Session, user: User) -> User:
        """Update last login.
        
        Args:
            db (Session): Database session.
            user (User): User model instance or payload.
        
        Returns:
            User: User data.
        """
        return UserRepository.update(db, user, {"last_login": datetime.now(UTC)})
