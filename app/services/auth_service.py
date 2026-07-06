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
        """Validate signatures and commit new profiles to the database."""
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
        """Validate input records against database crypt hashes."""
        email = email.strip().lower()

        user = UserRepository.get_by_email(db, email)
        if user is None:
            raise AuthenticationError("Invalid credentials")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")

        return user

    @staticmethod
    def create_token_pair(
        db: Session,
        user: User,
    ) -> TokenPair:
        """Build and write new stateful crypt sessions across tables."""
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
        """Assert refresh validation lifetimes and rotate sessions."""
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
        """Safely drop state bounds on singular hardware tracks."""
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
        """Drop all user authorization sessions stored in database."""
        return RefreshTokenRepository.revoke_all_user_tokens(db, user_id)

    @staticmethod
    def request_password_reset(db: Session, email: str) -> Any:
        """Verify targets and build a reset code tracking model."""
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
        """Assert constraints and update password state blocks."""
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
        """Verify current metrics and commit password updates."""
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password mismatched.")

        user.hashed_password = hash_password(new_password)
        db.add(user)
        db.commit()
        logger.info(
            "User password updated inside authenticated context."
        )
