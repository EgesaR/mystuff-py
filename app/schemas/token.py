"""Authentication token schemas and JWT payload structures."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TokenPair(BaseModel):
    """Internal DTO: Represents a pair of access and refresh tokens.
    Not exposed directly to the client; used to set HTTP-only cookies.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


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
