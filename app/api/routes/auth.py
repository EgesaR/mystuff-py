"""api/routes/auth.py
Authentication endpoints: register, login, refresh, logout, password management.

All business logic lives in AuthService.
This router only handles HTTP contracts.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
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
    ResetPasswordRequest,
    SignupRequest,
)
from app.schemas.token import RefreshRequest, TokenPair
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

logger = logging.getLogger("app")

router = APIRouter()


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
    """Register a new user and set authorization cookies."""
    try:
        user = AuthService.signup(
            db,
            email=payload.email,
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
        )
        tokens = AuthService.create_token_pair(db, user)

        # Standardize: Set cookies exactly like in /login
        response.set_cookie(
            key="access_token",
            value=tokens.access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="lax",
            max_age=3600
        )
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="lax",
            max_age=604800
        )

        return user
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc



# ── Login ─────────────────────────────────────────────────────────────────────


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,  # Add response injection
    db: Session = Depends(get_db),
):
    """Authenticate a user and set authorization cookies."""
    user = AuthService.authenticate(
        db, email=payload.email, password=payload.password
    )
    tokens = AuthService.create_token_pair(db, user)

    # Set cookies
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        secure=not settings.DEBUG,  # Must be True in production (HTTPS)
        samesite="lax",             # Helps prevent CSRF
        max_age=3600                # 1 hour
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=60 * 60 * 24 * 7    # 7 days
    )
    return user

# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotate refresh token and get a new token pair",
)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenPair:
    """Rotate an unexpired refresh token to yield clean authorization credentials."""
    try:
        return AuthService.refresh_tokens(db, payload.refresh_token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current refresh token",
)
def logout(
    response: Response,
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> None:
    """Invalidate a specific active refresh token session and clear cookies."""
    AuthService.logout(db, payload.refresh_token)

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

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
    """Invalidate all active token sessions across all user hardware endpoints."""
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
    """Initialize a recovery tracking state and send a transient recovery code out."""
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
    """Verify context token metrics and commit a new password string replacement."""
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
    """Update active user passwords by asserting the correctness of old passwords."""
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
    """Fetch profile parameters tied to the requesting active authorization token."""
    return current_user
