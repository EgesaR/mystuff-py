"""Authentication token schemas and JWT payload structures."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TokenPair(BaseModel):
    """Represents a pair of access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Schema for requesting a new token using a refresh token."""

    refresh_token: str


class AccessTokenPayload(BaseModel):
    """Payload structure for JWT access tokens."""

    sub: str
    exp: datetime
    iat: datetime
    type: Literal["access"]


class RefreshTokenPayload(BaseModel):
    """Payload structure for JWT refresh tokens."""

    sub: str
    exp: datetime
    iat: datetime
    type: Literal["refresh"]
