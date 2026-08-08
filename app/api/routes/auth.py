"""api/routes/auth.py
Authentication endpoints: register, login, refresh, logout, password management.

All business logic lives in AuthService.
This router only handles HTTP contracts.
"""
import logging
from typing import Literal, TypedDict

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_user
from app.api.deps.database import get_db
from app.core.config import settings
from app.core.errors import AuthenticationError, UserAlreadyExistsError
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    SignupRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService


class CookieOptions(TypedDict, total=False):
    """Options supported by Response.set_cookie()."""

    max_age: int
    expires: int | None
    path: str
    domain: str | None
    secure: bool
    httponly: bool
    samesite: Literal["lax", "strict", "none"]


class DeleteCookieOptions(TypedDict, total=False):
    """Options supported by Response.delete_cookie()."""

    path: str
    domain: str | None
    secure: bool
    httponly: bool
    samesite: Literal["lax", "strict", "none"]


logger = logging.getLogger("app")

router = APIRouter()


def get_cookie_options() -> DeleteCookieOptions:
    """Return common cookie options."""
    return {
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": (
            "none"
            if settings.ENVIRONMENT == "production"
            else "lax"
        ),
        "path": "/",
    }


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """Set authentication cookies."""

    access_options: CookieOptions = {
        **get_cookie_options(),
        "max_age": 60 * 60 * 24,
    }

    refresh_options: CookieOptions = {
        **get_cookie_options(),
        "max_age": 60 * 60 * 24 * 7,
    }

    print("========== COOKIE CONFIG ==========")
    print("Environment:", settings.ENVIRONMENT)
    print("DEBUG:", settings.DEBUG)
    print("Access cookie options:")
    print(access_options)
    print("Refresh cookie options:")
    print(refresh_options)
    print("Access token length:", len(access_token))
    print("Refresh token length:", len(refresh_token))
    print("===================================")

    response.set_cookie(
        key="access_token",
        value=access_token,
        **access_options,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        **refresh_options,
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    options = get_cookie_options()

    response.delete_cookie(
        "access_token",
        **options,
    )

    response.delete_cookie(
        "refresh_token",
        **options,
    )

# ── Register ─────────────────────────────────────────────────────────────────


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def signup(
    payload: SignupRequest,
    response: Response,  # Add this!
    db: Session = Depends(get_db),
):
    """Register a new user account.

    Args:
        payload (SignupRequest): Request payload.
        response (Response): HTTP response object.
        db (Session): Database session.

    Returns:
        Any: Result value.
    """
    try:
        user = AuthService.signup(
            db,
            email=payload.email,
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
        )
        tokens = AuthService.create_token_pair(db, user)

        # Set cookies
        set_auth_cookies(
            response,
            tokens.access_token,
            tokens.refresh_token,
        )

        return {
            "user": user,
            "access_token": tokens.access_token,
            "token_type": "bearer"
        }
        
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Login ─────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,  # Add response injection
    db: Session = Depends(get_db),
):
    """Authenticate a user and issue authorization cookies.

    Args:
        payload (LoginRequest): Request payload.
        response (Response): HTTP response object.
        db (Session): Database session.

    Returns:
        Any: Result value.
    """
    try:
        user = AuthService.authenticate(
            db, email=payload.email, password=payload.password
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid email or password") from exc

    tokens = AuthService.create_token_pair(db, user)

    set_auth_cookies(
        response,
        tokens.access_token,
        tokens.refresh_token,
    )

    return {
        "user": user,
        "access_token": tokens.access_token,
        "token_type": "bearer"
    }


# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    summary="Rotate refresh token and get a new token pair",
)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    """Refresh access and refresh tokens.

    Args:
        payload (RefreshRequest): Request payload.
        db (Session): Database session.

    Returns:
        TokenPair: TokenPair result.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    try:
        tokens = AuthService.refresh_tokens(db, refresh_token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    set_auth_cookies(
        response,
        tokens.access_token,
        tokens.refresh_token,
    )

    return {"message": "Tokens refreshed successfully"}


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current refresh token",
)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
) -> None:
    """Revoke the current refresh token and clear cookies.

    Args:
        response (Response): HTTP response object.
        payload (RefreshRequest): Request payload.
        db (Session): Database session.

    Returns:
        None: None result.
    """
    if refresh_token:
        AuthService.logout(db, refresh_token)

    clear_auth_cookies(response)

    # Returning None satisfies status_code=204
    return None


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke ALL refresh tokens for the current user",
)
def logout_all(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Revoke all refresh tokens for the current user.

    Args:
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.

    Returns:
        None: None result.
    """
    AuthService.logout_all_devices(db, current_user.id)


# ── Forgot / Reset password ───────────────────────────────────────────────────

@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request a password-reset code via email",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """Send a password reset code to the user email.

    Args:
        payload (ForgotPasswordRequest): Request payload.
        db (Session): Database session.

    Returns:
        ForgotPasswordResponse: ForgotPasswordResponse payload.
    """
    result = AuthService.request_password_reset(db, email=payload.email)

    response = ForgotPasswordResponse(
        message="If that email is registered, a reset code was sent."
    )

    if settings.DEMO_MODE and result is not None:
        response.code = result.code  # type: ignore[attr-defined]

    return response


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset password using a valid code",
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> None:
    """Reset a user password using a recovery code.

    Args:
        payload (ResetPasswordRequest): Request payload.
        db (Session): Database session.

    Returns:
        None: None result.
    """
    try:
        AuthService.reset_password(
            db,
            email=payload.email,
            code=payload.code,
            new_password=payload.new_password,
        )
    except (AuthenticationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Change password (authenticated) ──────────────────────────────────────────

@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password (requires current password)",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Change the current user password.

    Args:
        payload (ChangePasswordRequest): Request payload.
        current_user (User): Authenticated user performing the action.
        db (Session): Database session.

    Returns:
        None: None result.
    """
    try:
        AuthService.change_password(
            db,
            user=current_user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Me ────────────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the authenticated user's profile",
)
def me(
    current_user: User = Depends(require_active_user),
) -> User:
    """Return the authenticated user profile.

    Args:
        current_user (User): Authenticated user performing the action.

    Returns:
        User: User data.
    """
    return current_user
