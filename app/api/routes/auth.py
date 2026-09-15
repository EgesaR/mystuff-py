"""
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
from app.schemas.user import (
    BetaResponse,
    FeedbackResponse,
    UserOnboardingResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.onboarding_service import OnboardingService

logger = logging.getLogger("app")

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Cookie types
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Cookie helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_cookie_options() -> DeleteCookieOptions:
    """Return common authentication-cookie options."""

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
        key="access_token",
        **options,
    )

    response.delete_cookie(
        key="refresh_token",
        **options,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Onboarding helpers
# ─────────────────────────────────────────────────────────────────────────────

def onboarding_step_index(current_step: str) -> int:
    """
    Convert the persisted onboarding step name to its public integer index.

    Example:
        welcome   -> 0
        workspace -> 1
        features  -> 2
        feedback  -> 3
        beta      -> 4
        complete  -> 5
    """

    try:
        return settings.ONBOARDING_STEPS.index(current_step)
    except ValueError:
        logger.warning(
            "Unknown onboarding step '%s'; defaulting to 0",
            current_step,
        )
        return 0


def build_user_response(
    db: Session,
    user: User,
) -> UserResponse:
    """
    Build the API representation of a user.

    Onboarding.beta and onboarding.feedback are derived values and therefore
    must be constructed explicitly instead of serializing the SQLAlchemy
    UserOnboarding model directly.
    """

    onboarding = OnboardingService.build_state(
        db,
        user,
    )

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        is_active=user.is_active,
        is_developer=user.is_developer,
        is_admin=user.is_admin,
        onboarding=UserOnboardingResponse(
            required=onboarding.required,
            completed=onboarding.completed,
            step=onboarding_step_index(onboarding.current_step),
            skipped=onboarding.skipped,
            version=onboarding.version,
            completed_at=onboarding.completed_at,
            beta=BetaResponse(
                interested=onboarding.beta.interested,
                status=onboarding.beta.status,
                signed_up_at=onboarding.beta.signed_up_at,
            ),
            feedback=FeedbackResponse(
                submitted=onboarding.feedback.submitted,
                last_submitted_at=onboarding.feedback.last_submitted_at,
            ),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Signup
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/signup",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
def signup(
    payload: SignupRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Register a new user and issue authentication cookies."""

    try:
        user = AuthService.signup(
            db,
            email=payload.email,
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
        )

        tokens = AuthService.create_token_pair(
            db,
            user,
        )

        set_auth_cookies(
            response,
            tokens.access_token,
            tokens.refresh_token,
        )

        return LoginResponse(
            user=build_user_response(
                db,
                user,
            ),
            access_token=tokens.access_token,
            token_type="bearer",
        )

    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate a user",
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate a user and issue authentication cookies."""

    logger.info(
        "Login attempt for email=%s",
        payload.email,
    )

    try:
        user = AuthService.authenticate(
            db,
            email=payload.email,
            password=payload.password,
        )
    except AuthenticationError as exc:
        logger.warning(
            "Authentication failed for email=%s",
            payload.email,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc

    # Ensure onboarding exists and is at the current application version
    # before constructing the response.
    onboarding = OnboardingService.build_state(
        db,
        user,
    )

    tokens = AuthService.create_token_pair(
        db,
        user,
    )

    set_auth_cookies(
        response,
        tokens.access_token,
        tokens.refresh_token,
    )

    logger.info(
        "Login successful: email=%s step=%s version=%s",
        user.email,
        onboarding.current_step,
        onboarding.version,
    )

    return LoginResponse(
        user=build_user_response(
            db,
            user,
        ),
        access_token=tokens.access_token,
        token_type="bearer",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Refresh
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    summary="Rotate refresh token and get a new token pair",
)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Refresh access and refresh tokens."""

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
            detail=str(exc),
        ) from exc

    set_auth_cookies(
        response,
        tokens.access_token,
        tokens.refresh_token,
    )

    return {
        "message": "Tokens refreshed successfully",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current refresh token",
)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> None:
    """Revoke the current refresh token and clear cookies."""

    if refresh_token:
        AuthService.logout(
            db,
            refresh_token,
        )

    clear_auth_cookies(response)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke ALL refresh tokens for the current user",
)
def logout_all(
    response: Response,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Revoke all refresh tokens for the current user."""

    AuthService.logout_all_devices(
        db,
        current_user.id,
    )

    clear_auth_cookies(response)


# ─────────────────────────────────────────────────────────────────────────────
# Forgot password
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request a password-reset code via email",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """Request a password-reset code."""

    result = AuthService.request_password_reset(
        db,
        email=payload.email,
    )

    result_response = ForgotPasswordResponse(
        message="If that email is registered, a reset code was sent.",
    )

    if settings.DEMO_MODE and result is not None:
        result_response.code = result.code  # type: ignore[attr-defined]

    return result_response


# ─────────────────────────────────────────────────────────────────────────────
# Reset password
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password using a valid code",
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

        return {
            "message": "Password updated successfully.",
        }

    except (AuthenticationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Change password
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Current user
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the authenticated user's profile",
)
def me(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> UserResponse:
    """Return the authenticated user's complete profile."""

    result = build_user_response(
        db,
        current_user,
    )

    logger.debug(
        "Current user loaded: email=%s step=%s version=%s",
        current_user.email,
        result.onboarding.step,
        result.onboarding.version,
    )

    return result
