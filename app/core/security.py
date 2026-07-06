"""Authentication and security utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.schemas.token import (
    AccessTokenPayload,
    RefreshTokenPayload,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    # Bcrypt truncates passwords longer than 72 bytes.
    # We slice to ensure stability across platforms.
    pwd_bytes = password[:72].encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hash."""
    pwd_bytes = plain_password[:72].encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a new access token."""
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    now = datetime.now(UTC)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a new refresh token."""
    if expires_delta is None:
        expires_delta = timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )

    now = datetime.now(UTC)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": "refresh",
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(
    token: str,
) -> dict[str, Any] | None:
    """Decode a JWT token and return the payload."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

    except JWTError:
        return None


def decode_access_token(
    token: str,
) -> AccessTokenPayload | None:
    """Decode and validate an access token."""
    payload = decode_token(token)

    if payload is None:
        return None

    try:
        token_data = AccessTokenPayload.model_validate(
            payload,
        )

        return token_data

    # pylint: disable=broad-exception-caught
    except Exception:
        return None


def decode_refresh_token(
    token: str,
) -> RefreshTokenPayload | None:
    """Decode and validate a refresh token."""
    payload = decode_token(token)

    if payload is None:
        return None

    try:
        token_data = RefreshTokenPayload.model_validate(
            payload,
        )

        return token_data

    # pylint: disable=broad-exception-caught
    except Exception:
        return None
