"""Repository for authentication and password reset token operations."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.auth import PasswordResetToken, RefreshToken
from app.repositories.base_repository import BaseRepository


# pylint: disable=too-few-public-methods
class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository for managing refresh tokens."""

    model = RefreshToken

    @classmethod
    def create_token(
        cls, db: Session, *, token: str, user_id: str, expires_at: datetime
    ) -> RefreshToken:
        """Create a new refresh token record."""
        refresh_token = cls.model(
            token=token, user_id=user_id, expires_at=expires_at
        )
        try:
            db.add(refresh_token)
            db.commit()
            db.refresh(refresh_token)
            return refresh_token
        except Exception:
            db.rollback()
            raise

    @classmethod
    def get_valid_token(cls, db: Session, token: str) -> RefreshToken | None:
        """Retrieve a valid, non-revoked, unexpired refresh token."""
        return (
            db.query(cls.model)
            .filter(
                cls.model.token == token,
                cls.model.revoked.is_(False),
                cls.model.expires_at > datetime.now(UTC),
            )
            .first()
        )

    @classmethod
    def revoke_token(cls, db: Session, refresh_token: RefreshToken) -> RefreshToken:
        """Revoke a specific refresh token."""
        refresh_token.revoked = True
        try:
            db.commit()
            db.refresh(refresh_token)
            return refresh_token
        except Exception:
            db.rollback()
            raise

    @classmethod
    def revoke_all_user_tokens(cls, db: Session, user_id: str) -> int:
        """Revoke all active tokens for a given user."""
        try:
            count = (
                db.query(cls.model)
                .filter(cls.model.user_id == user_id, cls.model.revoked.is_(False))
                .update({"revoked": True}, synchronize_session=False)
            )
            db.commit()
            return count
        except Exception:
            db.rollback()
            raise


# pylint: disable=too-few-public-methods
class PasswordResetRepository(BaseRepository[PasswordResetToken]):
    """Repository for managing password reset tokens."""

    model = PasswordResetToken

    @classmethod
    def create_token(
        cls, db: Session, *, token: str, user_id: str, expires_at: datetime
    ) -> PasswordResetToken:
        """Create a new password reset token."""
        reset_token = cls.model(
            token=token, user_id=user_id, expires_at=expires_at
        )
        try:
            db.add(reset_token)
            db.commit()
            db.refresh(reset_token)
            return reset_token
        except Exception:
            db.rollback()
            raise

    @classmethod
    def get_valid_token(cls, db: Session, token: str) -> PasswordResetToken | None:
        """Retrieve a valid, unused, unexpired password reset token."""
        return (
            db.query(cls.model)
            .filter(
                cls.model.token == token,
                cls.model.used.is_(False),
                cls.model.expires_at > datetime.now(UTC),
            )
            .first()
        )

    @classmethod
    def mark_used(
        cls, db: Session, reset_token: PasswordResetToken
    ) -> PasswordResetToken:
        """Mark a password reset token as used."""
        reset_token.used = True
        try:
            db.commit()
            db.refresh(reset_token)
            return reset_token
        except Exception:
            db.rollback()
            raise
