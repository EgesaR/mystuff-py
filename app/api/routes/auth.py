"""Authentication endpoints for signup, login, sessions and password recovery."""

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
from app.services.user_response_service import build_user_response

logger = logging.getLogger("app")

router = APIRouter()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ACCESS_TOKEN_MAX_AGE = 60 * 60 * 24
REFRESH_TOKEN_MAX_AGE = 60 * 60 * 24 * 7


class CookieOptions(TypedDict, total=False):
    """Shared attributes supported by authentication cookie operations."""

    path: str
    domain: str | None
    secure: bool
    httponly: bool
    samesite: Literal["lax", "strict", "none"]


def get_cookie_options() -> CookieOptions:
    """Return consistent security attributes for authentication cookies."""
    production = settings.ENVIRONMENT == "production"

    return {
        "httponly": True,
        "secure": production or not settings.DEBUG,
        "samesite": "none" if production else "lax",
        "path": "/",
    }


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """Set the access and refresh token cookies."""
    options = get_cookie_options()

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        **options,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_MAX_AGE,
        **options,
    )


def clear_auth_cookies(response: Response) -> None:
    """Remove authentication cookies using matching cookie attributes."""
    options = get_cookie_options()

    response.delete_cookie(
        key="access_token",
        **options,
    )

    response.delete_cookie(
        key="refresh_token",
        **options,
    )


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


@router.post(
    "/signup",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
def signup(
    payload: SignupRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Register a new user and establish an authenticated session."""
    try:
        user = AuthService.signup(
            db,
            email=payload.email,
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
        )

    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    user_response = build_user_response(db, user)
    tokens = AuthService.create_token_pair(db, user)

    set_auth_cookies(
        response,
        tokens.access_token,
        tokens.refresh_token,
    )

    return LoginResponse(
        user=user_response,
        access_token=tokens.access_token,
        token_type="bearer",
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Sign in",
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate a user and issue a new token pair."""
    try:
        user = AuthService.authenticate(
            db,
            email=payload.email,
            password=payload.password,
        )

    except AuthenticationError as exc:
        logger.warning("Authentication failed")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc

    # Construct the user contract once, including onboarding information.
    user_response = build_user_response(db, user)

    tokens = AuthService.create_token_pair(db, user)

    set_auth_cookies(
        response,
        tokens.access_token,
        tokens.refresh_token,
    )

    logger.info(
        "Login successful: user=%s onboarding_step=%s version=%s",
        user.id,
        user_response.onboarding.step,
        user_response.onboarding.version,
    )

    return LoginResponse(
        user=user_response,
        access_token=tokens.access_token,
        token_type="bearer",
    )


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


@router.post(
    "/refresh",
    summary="Rotate the refresh token",
)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias="refresh_token",
    ),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Rotate the refresh token and issue a new access token."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        tokens = AuthService.refresh_tokens(
            db,
            refresh_token,
        )

    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired",
        ) from exc

    set_auth_cookies(
        response,
        tokens.access_token,
        tokens.refresh_token,
    )

    return {"message": "Session refreshed"}


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out this session",
)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias="refresh_token",
    ),
    db: Session = Depends(get_db),
) -> None:
    """Revoke the current refresh token and clear authentication cookies."""
    if refresh_token:
        AuthService.logout(db, refresh_token)

    clear_auth_cookies(response)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out all sessions",
)
def logout_all(
    response: Response,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Revoke all refresh tokens belonging to the current user."""
    AuthService.logout_all_devices(db, current_user.id)

    clear_auth_cookies(response)


# ---------------------------------------------------------------------------
# Password recovery
# ---------------------------------------------------------------------------


@router.post(
    "/password/forgot",
    response_model=ForgotPasswordResponse,
    summary="Request a password reset",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """Request a password reset without exposing account existence."""
    result = AuthService.request_password_reset(
        db,
        email=payload.email,
    )

    response = ForgotPasswordResponse(message="If that email is registered, a reset code was sent.")

    # Expose reset codes only in demo mode.
    if settings.DEMO_MODE and result is not None:
        response.code = result.code  # type: ignore[attr-defined]

    return response


@router.post(
    "/password/reset",
    summary="Reset a password",
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Reset a user's password using a valid recovery code."""
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

    return {"message": "Password updated"}


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------


@router.post(
    "/password/change",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the signed-in user's password",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Change the authenticated user's password."""
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


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the signed-in user",
)
def me(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Return the authenticated user's complete API representation."""
    return build_user_response(db, current_user)
