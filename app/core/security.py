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

SHARE_TOKEN_TYPE = "share"


def hash_password(password: str) -> str:
    """Hash a password for secure storage.

    Args:
        password (str): Password string.

    Returns:
        str: Processed string result.
    """
    # Bcrypt truncates passwords longer than 72 bytes.
    # We slice to ensure stability across platforms.
    pwd_bytes = password[:72].encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its stored hash.

    Args:
        plain_password (str): Plain password string.
        hashed_password (str): Hashed password string.

    Returns:
        bool: True if successful, False otherwise.
    """
    pwd_bytes = plain_password[:72].encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a new access token.

    Args:
        subject (str): Subject string.
        expires_delta (timedelta | None): The expires delta.

    Returns:
        str: Processed string result.
    """
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
    """Create a new refresh token.

    Args:
        subject (str): Subject string.
        expires_delta (timedelta | None): The expires delta.

    Returns:
        str: Processed string result.
    """
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


def create_share_token(
    *,
    owner_id: str,
    resource_type: str,
    resource_id: str,
    permission: str,
    target_user_id: str | None = None,
    expires_delta: timedelta | None = None
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "typ": SHARE_TOKEN_TYPE,
        "sub": owner_id,
        "res_type": resource_type,
        "res_id": resource_id,
        "per": permission,
        "target": target_user_id,
        "iat": now
    }
    if expires_delta is not None:
        payload["exp"] = now + expires_delta

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(
    token: str,
) -> dict[str, Any] | None:
    """Decode a JWT token payload.

    Args:
        token (str): Token string.

    Returns:
        dict[str, Any] | None: Response payload or None.
    """
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
    """Decode an access token payload.

    Args:
        token (str): Token string.

    Returns:
        AccessTokenPayload | None: AccessTokenPayload or None.
    """
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
    """Decode a refresh token payload.

    Args:
        token (str): Token string.

    Returns:
        RefreshTokenPayload | None: RefreshTokenPayload or None.
    """
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


def decode_share_token(token: str) -> dict[str, Any] | None:
    payload = decode_token(token)
    if payload is None or payload.get("typ") != SHARE_TOKEN_TYPE:
        return None
    return payload
