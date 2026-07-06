"""Pydantic models for authentication and password management."""

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    """Schema for user signup requests."""

    email: EmailStr
    username: str = Field(
        min_length=3,
        max_length=50,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    full_name: str | None = Field(
        default=None,
        max_length=255,
    )


class RefreshTokenRequest(BaseModel):
    """Schema for requesting a new token via a refresh token."""

    refresh_token: str


class LoginRequest(BaseModel):
    """Schema for user login credentials."""

    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    """Schema for initiating a password reset process."""

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Schema for the response after requesting a password reset."""

    message: str = "Password reset email sent successfully"
    code: str | None = None  # Allowed to be set if settings.DEBUG is True


class ResetPasswordRequest(BaseModel):
    """Schema for finalizing a password reset."""

    email: EmailStr
    code: str

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )


class ChangePasswordRequest(BaseModel):
    """Schema for changing an existing password."""

    current_password: str

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )
