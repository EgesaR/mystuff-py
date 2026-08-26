"""Core authentication business logic controller."""

import logging
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AuthenticationError, UserAlreadyExistsError
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
from app.services.email_service import EmailService

logger = logging.getLogger("app")


class PasswordResetTokenStub:
    """Transient structure to hold tracking variables during tests or DEMO_MODE."""

    def __init__(self, code: str):
        self.code = code


class AuthService:
    """Business transactions for public security and auth routing schemas."""

    @staticmethod
    def _generate_numeric_code(length: int = 6) -> str:
        """Generate a cryptographically secure numeric string code."""
        return "".join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def signup(
        db: Session,
        email: str,
        username: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """Register a new user account."""
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
    def authenticate(db: Session, email: str, password: str) -> User:
        """Authenticate user by email and password credentials."""
        email = email.strip().lower()

        user = UserRepository.get_by_email(db, email)
        if user is None:
            raise AuthenticationError("User doesn't exist")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")

        return user

    @staticmethod
    def create_token_pair(db: Session, user: User) -> TokenPair:
        """Generate and store access and refresh token pair."""
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        RefreshTokenRepository.create_token(
            db,
            token=refresh_token,
            user_id=user.id,
            expires_at=datetime.now(
                UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @staticmethod
    def refresh_tokens(db: Session, refresh_token: str) -> TokenPair:
        """Validate refresh token and issue a fresh pair."""
        payload = decode_refresh_token(refresh_token)
        if payload is None:
            raise AuthenticationError("Invalid refresh token")

        token_record = RefreshTokenRepository.get_valid_token(
            db, refresh_token)
        if token_record is None:
            raise AuthenticationError("Refresh token revoked")

        RefreshTokenRepository.revoke_token(db, token_record)
        return AuthService.create_token_pair(db, token_record.user)

    @staticmethod
    def logout(db: Session, refresh_token: str) -> None:
        """Revoke active refresh token."""
        token_record = RefreshTokenRepository.get_valid_token(
            db, refresh_token)
        if token_record:
            RefreshTokenRepository.revoke_token(db, token_record)

    @staticmethod
    def logout_all_devices(db: Session, user_id: str) -> int:
        """Revoke all active refresh tokens for a user."""
        return RefreshTokenRepository.revoke_all_user_tokens(db, user_id)

    @staticmethod
    def request_password_reset(db: Session, email: str) -> Any:
        """Request password reset code and dispatch email notification."""
        email = email.strip().lower()
        user = UserRepository.get_by_email(db, email)

        if not user:
            # Prevents email enumeration by failing silently
            return None

        code = AuthService._generate_numeric_code(6)
        user.reset_code = code
        user.reset_code_expires_at = datetime.now(UTC) + timedelta(minutes=15)

        db.add(user)
        db.commit()

        email_sent = EmailService.send_reset_code(
            email=user.email,
            code=code,
            username=user.username,
        )

        if not email_sent:
            logger.error(
                "Failed to dispatch password reset email to: %s", email)
        else:
            logger.info(
                "Password reset code generated and dispatched for: %s", email)

        return PasswordResetTokenStub(code=code)

    @staticmethod
    def reset_password(
        db: Session, email: str, code: str, new_password: str
    ) -> None:
        """Reset user password using verification code."""
        email = email.strip().lower()
        user = UserRepository.get_by_email(db, email)

        if not user:
            raise AuthenticationError("Invalid profile recovery parameters.")

        if (
            not user.reset_code
            or user.reset_code != code
            or not user.reset_code_expires_at
            or user.reset_code_expires_at < datetime.now(UTC)
        ):
            raise ValueError("Invalid or expired confirmation code.")

        user.hashed_password = hash_password(new_password)
        user.reset_code = None
        user.reset_code_expires_at = None

        db.add(user)
        db.commit()
        logger.info("Password updated successfully for: %s", email)

    @staticmethod
    def change_password(
        db: Session, user: User, current_password: str, new_password: str
    ) -> None:
        """Change current password inside authenticated context."""
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password mismatched.")

        user.hashed_password = hash_password(new_password)
        db.add(user)
        db.commit()
        logger.info("User password updated inside authenticated context.")
