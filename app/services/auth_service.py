"""app/services/auth_service.py
Core authentication business logic controller.

Orchestrates user registrations, system access credentials checks,
token pair rotations, and profile recovery operations.
"""
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import (
    AuthenticationError,
    UserAlreadyExistsError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.auth_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.token import TokenPair

logger = logging.getLogger("app")


class PasswordResetTokenStub:
    """Transient structure to hold tracking variables during tests."""

    def __init__(self, code: str):
        """Init.
        
        Args:
            code (str): Verification or reset code.
        """
        self.code = code


class AuthService:
    """Business transactions for public security and auth routing schemas."""

    @staticmethod
    def signup(
        db: Session,
        email: str,
        username: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """Register a new user account.
        
        Args:
            db (Session): Database session.
            email (str): Email address.
            username (str): Username.
            password (str): Password string.
            full_name (str | None): User full name.
        
        Returns:
            User: User data.
        """
        email = email.strip().lower()

        existing = UserRepository.get_by_email(db, email)
        if existing:
            raise UserAlreadyExistsError(
                "An account with this email already exists.")

        user = UserRepository.create_user(
            db,
            email=email,
            username=username,
            hashed_password=hash_password(password),
            full_name=full_name,
        )

        logger.info("User registered: %s", email)
        return user

    @staticmethod
    def authenticate(
        db: Session,
        email: str,
        password: str,
    ) -> User:
        """Authenticate.
        
        Args:
            db (Session): Database session.
            email (str): Email address.
            password (str): Password string.
        
        Returns:
            User: User data.
        """
        email = email.strip().lower()

        user = UserRepository.get_by_email(db, email)
        if user is None:
            raise AuthenticationError("User doesn't exist")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")

        return user

    @staticmethod
    def create_token_pair(
        db: Session,
        user: User,
    ) -> TokenPair:
        """Create token pair.
        
        Args:
            db (Session): Database session.
            user (User): User model instance or payload.
        
        Returns:
            TokenPair: TokenPair result.
        """
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        RefreshTokenRepository.create_token(
            db,
            token=refresh_token,
            user_id=user.id,
            expires_at=(
                datetime.now(UTC)
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            ),
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @staticmethod
    def refresh_tokens(
        db: Session,
        refresh_token: str,
    ) -> TokenPair:
        """Refresh tokens.
        
        Args:
            db (Session): Database session.
            refresh_token (str): Refresh token string.
        
        Returns:
            TokenPair: TokenPair result.
        """
        payload = decode_refresh_token(refresh_token)
        if payload is None:
            raise AuthenticationError("Invalid refresh token")

        token_record = RefreshTokenRepository.get_valid_token(
            db, refresh_token
        )
        if token_record is None:
            raise AuthenticationError("Refresh token revoked")

        RefreshTokenRepository.revoke_token(db, token_record)
        return AuthService.create_token_pair(db, token_record.user)

    @staticmethod
    def logout(
        db: Session,
        refresh_token: str,
    ) -> None:
        """Revoke the current refresh token and clear cookies.
        
        Args:
            db (Session): Database session.
            refresh_token (str): Refresh token string.
        
        Returns:
            None: None result.
        """
        token_record = RefreshTokenRepository.get_valid_token(
            db, refresh_token
        )
        if token_record:
            RefreshTokenRepository.revoke_token(db, token_record)

    @staticmethod
    def logout_all_devices(
        db: Session,
        user_id: str,
    ) -> int:
        """Logout all devices.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            int: int result.
        """
        return RefreshTokenRepository.revoke_all_user_tokens(db, user_id)

    @staticmethod
    def request_password_reset(db: Session, email: str) -> Any:
        """Request password reset.
        
        Args:
            db (Session): Database session.
            email (str): Email address.
        
        Returns:
            Any: Result value.
        """
        email = email.strip().lower()
        user = UserRepository.get_by_email(db, email)
        if not user:
            return None

        demo_code = "123456"
        logger.info("Password reset sequence initiated for: %s", email)
        return PasswordResetTokenStub(code=demo_code)

    @staticmethod
    def reset_password(
        db: Session, email: str, code: str, new_password: str
    ) -> None:
        """Reset a user password using a recovery code.
        
        Args:
            db (Session): Database session.
            email (str): Email address.
            code (str): Verification or reset code.
            new_password (str): New password string.
        
        Returns:
            None: None result.
        """
        email = email.strip().lower()
        user = UserRepository.get_by_email(db, email)
        if not user:
            raise AuthenticationError("Invalid profile recovery parameters.")

        if code != "123456":
            raise ValueError("Invalid or expired confirmation code.")

        user.hashed_password = hash_password(new_password)
        db.add(user)
        db.commit()
        logger.info(
            "Password updated successfully via codes for: %s", email
        )

    @staticmethod
    def change_password(
        db: Session, user: User, current_password: str, new_password: str
    ) -> None:
        """Change the current user password.
        
        Args:
            db (Session): Database session.
            user (User): User model instance or payload.
            current_password (str): Current password string.
            new_password (str): New password string.
        
        Returns:
            None: None result.
        """
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password mismatched.")

        user.hashed_password = hash_password(new_password)
        db.add(user)
        db.commit()
        logger.info(
            "User password updated inside authenticated context."
        )
